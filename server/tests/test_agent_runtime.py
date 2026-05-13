from __future__ import annotations


def test_settings_resolve_deepseek_provider_profile_defaults(temp_app_env, monkeypatch):
    from inkvault_server.core.config import get_settings

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("INKVAULT_AGENT_PROVIDER_PROFILE", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test-key")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.agent_provider_profile == "deepseek"
    assert settings.agent_provider_name == "deepseek"
    assert settings.agent_provider_model == "deepseek-v4-flash"
    assert settings.agent_provider_base_url == "https://api.deepseek.com"
    assert settings.agent_provider_api_key == "deepseek-test-key"
    assert settings.agent_provider_structured_output_method == "json_mode"


def test_settings_resolve_embedding_provider_profile_defaults(temp_app_env, monkeypatch):
    from inkvault_server.core.config import get_settings

    monkeypatch.setenv("INKVAULT_EMBEDDING_PROVIDER_PROFILE", "openai")
    monkeypatch.setenv("INKVAULT_EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("INKVAULT_EMBEDDING_API_KEY", "embedding-test-key")
    monkeypatch.setenv("INKVAULT_EMBEDDING_BASE_URL", "https://example.com/embeddings")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.embedding_provider_profile == "openai"
    assert settings.embedding_provider_name == "openai"
    assert settings.embedding_provider_model == "text-embedding-3-small"
    assert settings.embedding_provider_base_url == "https://example.com/embeddings"
    assert settings.embedding_provider_api_key == "embedding-test-key"


def test_agent_runtime_answers_without_model_credentials(temp_app_env):
    from inkvault_server.agents import AgentRuntime, AskRequestModel, CitationModel
    from inkvault_server.core.config import get_settings

    runtime = AgentRuntime(get_settings())
    response = runtime.answer(
        AskRequestModel(
            question="这个主题现在最稳定的理解是什么？",
            mode="vault",
            pendingReviewCount=0,
            citations=[
                CitationModel(
                    id="source-001",
                    title="Research-first wiki note",
                    kind="WEB",
                    excerpt="这是来源摘录。",
                    locator="https://example.com/source-001",
                    vaultPath="raw/source-001.md",
                )
            ],
        )
    )

    assert response.answer
    assert response.citationSourceIds == ["source-001"]


def test_agent_runtime_routes_vault_only_runs_directly_to_answer(temp_app_env):
    from inkvault_server.agents import AgentRuntime, AskRequestModel, CitationModel
    from inkvault_server.core.config import get_settings

    runtime = AgentRuntime(get_settings())
    assert runtime._ask_graph is not None
    request = AskRequestModel(
        question="这个主题现在最稳定的理解是什么？",
        mode="vault",
        pendingReviewCount=0,
        citations=[
            CitationModel(
                id="source-001",
                title="Research-first wiki note",
                kind="WEB",
                excerpt="这是来源摘录。",
                locator="https://example.com/source-001",
                vaultPath="raw/source-001.md",
            )
        ],
    )
    state = {"request": request}
    state.update(runtime._load_request_context(state))
    state.update(runtime._retrieve_vault_context(state))
    assessment = runtime._assess_evidence(state)

    assert assessment["needs_web_assist"] is False
    assert runtime._route_after_assessment({**state, **assessment}) == "answer"

    response = runtime.answer(request)

    assert response.usedWebSources == []


def test_agent_runtime_routes_vault_plus_web_through_web_branch_when_vault_evidence_is_thin(temp_app_env):
    from inkvault_server.agents import AgentRuntime, AskRequestModel
    from inkvault_server.core.config import get_settings

    runtime = AgentRuntime(get_settings(), web_assist_provider=lambda _query: [])
    request = AskRequestModel(
        question="补充外部视角",
        mode="vault_plus_web",
        pendingReviewCount=1,
    )
    state = {"request": request}
    state.update(runtime._load_request_context(state))
    state.update(runtime._retrieve_vault_context(state))
    assessment = runtime._assess_evidence(state)

    assert assessment["needs_web_assist"] is True
    assert runtime._route_after_assessment({**state, **assessment}) == "web"

    response = runtime.answer(request)

    assert response.knowledgeGaps
    assert response.canWriteback is True


def test_agent_runtime_uses_web_assist_when_initial_vault_answer_still_has_knowledge_gaps(temp_app_env, monkeypatch):
    from inkvault_server import agents
    from inkvault_server.core.config import get_settings

    captured_prompts: list[str] = []
    web_queries: list[str] = []

    class FakeStructuredAskLLM:
        def invoke(self, prompt):
            captured_prompts.append(prompt)
            if "External web evidence:" in prompt:
                return agents.AskStructuredOutput(
                    answer="结合外部补料后，可以确认这个主题的最新变化来自新增网页证据。",
                    confidence=0.92,
                    followUpQuestions=["这条外部资料是否值得沉淀进 wiki？"],
                    knowledgeGaps=[],
                    citationSourceIds=["source-001"],
                )
            return agents.AskStructuredOutput(
                answer="仅基于 vault，目前还缺少一条更新的外部证据。",
                confidence=0.67,
                followUpQuestions=["还缺少哪条更新来源？"],
                knowledgeGaps=["需要更多外部时间线来源。"],
                citationSourceIds=["source-001"],
            )

    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def with_structured_output(self, _schema, **_kwargs):
            return FakeStructuredAskLLM()

    def fake_web_assist(query: str):
        web_queries.append(query)
        return [
            {
                "url": "https://example.com/new-evidence",
                "title": "New Evidence",
                "excerpt": "这条外部网页补足了最新变化的时间线证据。",
                "reason_used": "它补足了 vault 当前缺失的外部时间线来源。",
            }
        ]

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    get_settings.cache_clear()
    monkeypatch.setattr(agents, "ChatOpenAI", FakeChatOpenAI)

    runtime = agents.AgentRuntime(get_settings(), web_assist_provider=fake_web_assist)
    response = runtime.answer(
        agents.AskRequestModel(
            question="这个主题的最新变化是什么？",
            mode="vault_plus_web",
            pendingReviewCount=0,
            topic=agents.TopicModel(
                id="topic-001",
                title="Vault-first LLM Wiki",
                currentUnderstanding=["当前 wiki 已经总结了基础定位。"],
                openQuestions=["最新变化还缺一条外部来源。"],
            ),
            citations=[
                agents.CitationModel(
                    id="source-001",
                    title="Research-first wiki note",
                    kind="WEB",
                    excerpt="这是来源摘录。",
                    locator="https://example.com/source-001",
                    vaultPath="raw/source-001.md",
                )
            ],
        )
    )

    assert web_queries == ["这个主题的最新变化是什么？"]
    assert len(captured_prompts) == 2
    assert "External web evidence:" not in captured_prompts[0]
    assert "External web evidence:" in captured_prompts[1]
    assert response.answer == "结合外部补料后，可以确认这个主题的最新变化来自新增网页证据。"
    assert response.usedWebSources == [
        agents.WebCitationModel(
            url="https://example.com/new-evidence",
            title="New Evidence",
            excerpt="这条外部网页补足了最新变化的时间线证据。",
            reasonUsed="它补足了 vault 当前缺失的外部时间线来源。",
        )
    ]
    assert response.writebackPackage is not None
    assert response.writebackPackage.usedWebSources == response.usedWebSources


def test_agent_runtime_flows_concrete_web_evidence_and_writeback_package_from_answer(temp_app_env):
    from inkvault_server.agents import AgentRuntime, AskRequestModel, AskWritebackPackageModel, WebCitationModel
    from inkvault_server.core.config import get_settings

    web_source = WebCitationModel(
        url="https://example.com/evidence",
        title="External Evidence",
        excerpt="New context from the web.",
        reasonUsed="It fills a known knowledge gap.",
    )
    writeback_package = AskWritebackPackageModel(
        topicDecision="PATCH",
        targetTopicId="topic-001",
        proposedUnderstanding="The current answer should update the topic summary.",
        proposedClaim="External evidence supports the answer.",
        proposedOpenQuestion="What changed since the previous source snapshot?",
        usedWebSources=[web_source],
    )

    class FakeAskGraph:
        def invoke(self, _):
            return {
                "answer": "Grounded answer with external evidence.",
                "confidence": 0.93,
                "follow_up_questions": ["What should we verify next?"],
                "knowledge_gaps": ["We still need one newer source."],
                "citation_source_ids": ["source-001"],
                "used_web_sources": [web_source],
                "context_ask_turn_ids": ["ask-prev"],
                "can_writeback": False,
                "writeback_package": writeback_package,
            }

    runtime = AgentRuntime(get_settings())
    runtime._ask_llm = object()
    runtime._ask_graph = FakeAskGraph()
    response = runtime.answer(
        AskRequestModel(
            question="延续上一轮，下一步应该补什么证据？",
            mode="vault_plus_web",
            pendingReviewCount=2,
        )
    )

    assert response.answer == "Grounded answer with external evidence."
    assert response.contextAskTurnIds == ["ask-prev"]
    assert response.usedWebSources == [web_source]
    assert response.canWriteback is False
    assert response.writebackPackage == writeback_package


def test_agent_runtime_generates_deterministic_workspace_briefing_without_model_credentials(temp_app_env):
    from inkvault_server.agents import AgentRuntime, AskBriefingRequestModel, AskBriefingSignalModel, CitationModel
    from inkvault_server.core.config import get_settings

    runtime = AgentRuntime(get_settings())
    response = runtime.brief(
        AskBriefingRequestModel(
            scope="workspace",
            pendingReviewCount=3,
            focusTopicTitle="Inkvault repositioning",
            recentSourceTitles=["Research-first wiki note"],
            healthSignals=[
                AskBriefingSignalModel(
                    type="RAW_BACKLOG",
                    title="raw 里有 3 条材料等待编译",
                    summary="这些材料还没有进入 wiki。",
                    href="/app/raw",
                ),
                AskBriefingSignalModel(
                    type="REVIEW_BACKLOG",
                    title="ingest 队列有 3 条待审阅提案",
                    summary="这些提案需要人工确认。",
                    href="/app/ingest",
                ),
                AskBriefingSignalModel(
                    type="UNSUPPORTED_CLAIM",
                    title="有 1 条 claim 缺少直接证据",
                    summary="至少有一条关键结论还没有直接证据链支持。",
                    href="/app/wiki",
                ),
            ],
            citations=[
                CitationModel(
                    id="source-001",
                    title="Research-first wiki note",
                    kind="WEB",
                    excerpt="强调 wiki-first 的研究工作流。",
                    locator="https://example.com/wiki",
                    vaultPath="raw/source-001.md",
                )
            ],
            suggestedQuestions=["当前最值得先审阅哪条迁移提案？"],
        )
    )

    assert response.scope == "workspace"
    assert response.summary
    assert response.knowledgeGaps
    assert any(gap.title == "有 1 条 claim 缺少直接证据" for gap in response.knowledgeGaps)
    assert response.nextActions
    assert response.suggestedQuestions
    assert response.supportingSignals


def test_agent_runtime_uses_real_briefing_llm_with_structured_provider_when_credentials_present(temp_app_env, monkeypatch):
    from inkvault_server import agents
    from inkvault_server.core.config import get_settings

    captured: dict[str, object] = {"schemas": [], "methods": []}

    class FakeStructuredBriefingLLM:
        def invoke(self, prompt):
            captured["prompt"] = prompt
            return agents.AskBriefingStructuredOutput(
                summary="当前最值得先处理的是 ingest 队列。",
                confidence=0.88,
                knowledgeGaps=[
                    agents.AskBriefingGapStructuredOutput(
                        title="待审阅提案积压",
                        detail="还有 3 条 ingest 提案没有进入最终知识层。",
                        href="/app/ingest",
                    )
                ],
                nextActions=[
                    agents.AskBriefingActionStructuredOutput(
                        kind="OPEN_INGEST",
                        label="打开审阅队列",
                        description="先处理最靠前的提案，再继续提问。",
                        href="/app/ingest",
                    )
                ],
                suggestedQuestions=["当前哪条提案最值得先审阅？"],
                supportingSignals=[
                    agents.AskBriefingSignalModel(
                        type="REVIEW_BACKLOG",
                        title="ingest 队列有 3 条待审阅提案",
                        summary="这些提案需要人工确认。",
                        href="/app/ingest",
                    )
                ],
            )

    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def with_structured_output(self, schema, **kwargs):
            captured["schemas"].append(schema)
            captured["methods"].append(kwargs.get("method"))
            return FakeStructuredBriefingLLM()

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    get_settings.cache_clear()
    monkeypatch.setattr(agents, "ChatOpenAI", FakeChatOpenAI)

    runtime = agents.AgentRuntime(get_settings())
    response = runtime.brief(
        agents.AskBriefingRequestModel(
            scope="workspace",
            pendingReviewCount=3,
            focusTopicTitle="Inkvault repositioning",
            recentSourceTitles=["Research-first wiki note"],
            healthSignals=[
                agents.AskBriefingSignalModel(
                    type="REVIEW_BACKLOG",
                    title="ingest 队列有 3 条待审阅提案",
                    summary="这些提案需要人工确认。",
                    href="/app/ingest",
                )
            ],
            citations=[],
            suggestedQuestions=["当前哪条提案最值得先审阅？"],
        )
    )

    assert captured["schemas"] == [agents.AskStructuredOutput, agents.CompileStructuredOutput, agents.AskBriefingStructuredOutput]
    assert captured["methods"] == ["json_schema", "json_schema", "json_schema"]
    assert "Briefing scope: workspace" in str(captured["prompt"])
    assert response.summary == "当前最值得先处理的是 ingest 队列。"
    assert response.nextActions[0].kind == "OPEN_INGEST"


def test_agent_runtime_falls_back_to_deterministic_briefing_when_provider_invoke_fails(temp_app_env, monkeypatch):
    from inkvault_server import agents
    from inkvault_server.core.config import get_settings

    class FailingStructuredBriefingLLM:
        def invoke(self, _prompt):
            raise RuntimeError("provider unavailable")

    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def with_structured_output(self, schema, **_kwargs):
            if schema is agents.AskBriefingStructuredOutput:
                return FailingStructuredBriefingLLM()
            return object()

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    get_settings.cache_clear()
    monkeypatch.setattr(agents, "ChatOpenAI", FakeChatOpenAI)

    runtime = agents.AgentRuntime(get_settings())
    response = runtime.brief(
        agents.AskBriefingRequestModel(
            scope="ask_turn",
            askTurnId="ask-001",
            topicTitle="Inkvault repositioning",
            askQuestion="这个主题当前最稳定的理解是什么？",
            askAnswer="当前最稳定的理解是 wiki 是新的核心对象。",
            askKnowledgeGaps=["当前还缺少最新外部资料。"],
            canWriteback=True,
            pendingReviewCount=1,
            focusTopicTitle="Inkvault repositioning",
            recentSourceTitles=["Research-first wiki note"],
            healthSignals=[],
            citations=[],
            suggestedQuestions=["下一步最值得补哪条证据？"],
        )
    )

    assert response.scope == "ask_turn"
    assert response.knowledgeGaps[0].title
    assert response.nextActions[0].href


def test_ask_structured_output_normalizes_confidence_labels():
    from inkvault_server.agents import AskStructuredOutput

    result = AskStructuredOutput(
        answer="answer",
        confidence="high",
        followUpQuestions=[],
        knowledgeGaps=[],
        citationSourceIds=[],
    )

    assert result.confidence == 0.85


def test_compile_structured_output_joins_open_question_lists():
    from inkvault_server.agents import CompileStructuredOutput

    result = CompileStructuredOutput(
        kind="RESEARCH_PROPOSAL",
        title="title",
        summary="summary",
        proposedTopicTitle="topic",
        proposedUnderstanding="understanding",
        proposedOpenQuestions=["q1", "q2"],
        proposedClaim="claim",
    )

    assert result.proposedOpenQuestions == "q1；q2"


def test_agent_runtime_compiles_without_model_credentials(temp_app_env):
    from inkvault_server.agents import AgentRuntime, CitationModel, CompileRequestModel, SourceModel
    from inkvault_server.core.config import get_settings

    runtime = AgentRuntime(get_settings())
    response = runtime.compile(
        CompileRequestModel(
            source=SourceModel(
                id="source-001",
                title="Research-first wiki note",
                kind="WEB",
                excerpt="这是来源摘录。",
                body="这是来源正文。",
                locator="https://example.com/source-001",
                vaultPath="raw/source-001.md",
            ),
            citations=[
                CitationModel(
                    id="chunk-topic-001",
                    title="Vault-first LLM Wiki",
                    kind="TOPIC",
                    excerpt="当前 wiki 的核心理解是把产品中心收回到 raw / ingest / wiki。",
                    vaultPath="wiki/vault-first-llm-wiki.md",
                )
            ],
        )
    )

    assert response.kind in {"TOPIC_CREATE", "TOPIC_PATCH"}
    assert response.proposedUnderstanding


def test_agent_runtime_normalizes_unknown_compile_kind_from_provider(temp_app_env, monkeypatch):
    from inkvault_server import agents
    from inkvault_server.core.config import get_settings

    class FakeStructuredCompileLLM:
        def invoke(self, _prompt):
            return agents.CompileStructuredOutput(
                kind="RESEARCH_PROPOSAL",
                title="title",
                summary="summary",
                proposedTopicTitle="topic",
                proposedUnderstanding="understanding",
                proposedOpenQuestions="q1",
                proposedClaim="claim",
            )

    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def with_structured_output(self, _schema, **_kwargs):
            return FakeStructuredCompileLLM()

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    get_settings.cache_clear()
    monkeypatch.setattr(agents, "ChatOpenAI", FakeChatOpenAI)

    runtime = agents.AgentRuntime(get_settings())
    response = runtime.compile(
        agents.CompileRequestModel(
            source=agents.SourceModel(
                id="source-001",
                title="Research-first wiki note",
                kind="WEB",
                excerpt="这是来源摘录。",
                body="这是来源正文。",
                locator="https://example.com/source-001",
                vaultPath="raw/source-001.md",
            )
        )
    )

    assert response.kind == "TOPIC_CREATE"


def test_agent_runtime_uses_real_ask_llm_with_structured_provider_when_credentials_present(temp_app_env, monkeypatch):
    from inkvault_server import agents
    from inkvault_server.core.config import get_settings

    captured: dict[str, object] = {"schemas": [], "init_kwargs": [], "methods": []}

    class FakeStructuredAskLLM:
        def invoke(self, prompt):
            captured["prompt"] = prompt
            return agents.AskStructuredOutput(
                answer="这是由真实 provider 路径生成的回答。",
                confidence=0.94,
                followUpQuestions=["下一步还要验证哪条来源？"],
                knowledgeGaps=["还缺少一条更近的来源。"],
                citationSourceIds=["source-001"],
            )

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured["init_kwargs"].append(kwargs)

        def with_structured_output(self, schema, **kwargs):
            captured["schemas"].append(schema)
            captured["methods"].append(kwargs.get("method"))
            return FakeStructuredAskLLM()

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("INKVAULT_AGENT_MODEL", "gpt-test")
    monkeypatch.setenv("INKVAULT_AGENT_CONNECT_TIMEOUT_SECONDS", "3.5")
    monkeypatch.setenv("INKVAULT_AGENT_READ_TIMEOUT_SECONDS", "12.0")
    get_settings.cache_clear()
    monkeypatch.setattr(agents, "ChatOpenAI", FakeChatOpenAI)

    runtime = agents.AgentRuntime(get_settings())
    response = runtime.answer(
        agents.AskRequestModel(
            question="这个主题现在最稳定的理解是什么？",
            mode="vault",
            pendingReviewCount=0,
            citations=[
                agents.CitationModel(
                    id="source-001",
                    title="Research-first wiki note",
                    kind="WEB",
                    excerpt="这是来源摘录。",
                    locator="https://example.com/source-001",
                    vaultPath="raw/source-001.md",
                )
            ],
        )
    )

    assert captured["schemas"] == [
        agents.AskStructuredOutput,
        agents.CompileStructuredOutput,
        agents.AskBriefingStructuredOutput,
    ]
    assert captured["methods"] == ["json_schema", "json_schema", "json_schema"]
    assert captured["init_kwargs"][0] == {
        "model": "gpt-test",
        "api_key": "test-openai-key",
        "base_url": "https://example.com/v1",
        "temperature": 0.1,
        "timeout": (3.5, 12.0),
    }
    assert "Question: 这个主题现在最稳定的理解是什么？" in str(captured["prompt"])
    assert response.answer == "这是由真实 provider 路径生成的回答。"
    assert response.citationSourceIds == ["source-001"]


def test_agent_runtime_backfills_langchain_llm_cache_for_real_provider(temp_app_env, monkeypatch):
    from types import SimpleNamespace

    from inkvault_server import agents
    from inkvault_server.core.config import get_settings

    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def with_structured_output(self, _schema, **_kwargs):
            return object()

    fake_langchain = SimpleNamespace(debug=False, verbose=False)

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    get_settings.cache_clear()
    monkeypatch.setattr(agents, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(agents, "langchain", fake_langchain)

    agents.AgentRuntime(get_settings())

    assert hasattr(fake_langchain, "llm_cache")
    assert fake_langchain.llm_cache is None


def test_agent_runtime_uses_json_mode_for_deepseek_structured_output(temp_app_env, monkeypatch):
    from inkvault_server import agents
    from inkvault_server.core.config import get_settings

    captured: dict[str, object] = {"calls": [], "init_kwargs": []}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured["init_kwargs"].append(kwargs)

        def with_structured_output(self, schema, **kwargs):
            captured["calls"].append((schema, kwargs.get("method")))
            return object()

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("INKVAULT_AGENT_PROVIDER_PROFILE", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(agents, "ChatOpenAI", FakeChatOpenAI)

    agents.AgentRuntime(get_settings())

    assert captured["calls"] == [
        (agents.AskStructuredOutput, "json_mode"),
        (agents.CompileStructuredOutput, "json_mode"),
        (agents.AskBriefingStructuredOutput, "json_mode"),
    ]
    assert captured["init_kwargs"][0]["api_key"] == "deepseek-test-key"
    assert captured["init_kwargs"][0]["base_url"] == "https://api.deepseek.com"
    assert captured["init_kwargs"][0]["model"] == "deepseek-v4-flash"


def test_agent_runtime_normalizes_compile_language_and_card_title_for_chinese_sources(temp_app_env, monkeypatch):
    from inkvault_server import agents
    from inkvault_server.core.config import get_settings

    class FakeStructuredCompileLLM:
        def invoke(self, _prompt):
            return agents.CompileStructuredOutput(
                kind="TOPIC_CREATE",
                title="Exploring Karpathy's LLM Knowledge Bases Framework",
                summary="This research aims to analyze and operationalize Karpathy's concept.",
                proposedTopicTitle="Exploring Karpathy's LLM Knowledge Bases Framework",
                proposedUnderstanding="This research aims to analyze and operationalize Karpathy's concept.",
                proposedOpenQuestions="How should this be adapted into the product?",
                proposedClaim="Karpathy's framework can be used as a practical foundation.",
            )

    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def with_structured_output(self, _schema, **_kwargs):
            return FakeStructuredCompileLLM()

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    get_settings.cache_clear()
    monkeypatch.setattr(agents, "ChatOpenAI", FakeChatOpenAI)

    runtime = agents.AgentRuntime(get_settings())
    response = runtime.compile(
        agents.CompileRequestModel(
            source=agents.SourceModel(
                id="source-001",
                title="Karpathy的LLM Wiki：为什么个人知识库的终极形态不是RAG，而是一个自维护的Wiki | FluxWise",
                kind="WEB",
                excerpt="Karpathy 提出的核心是让 LLM 持续维护结构化 wiki，而不是只做被动检索。",
                body="Karpathy 提出的核心是让 LLM 持续维护结构化 wiki，而不是只做被动检索。",
                locator="https://example.com/source-001",
                vaultPath="raw/source-001.md",
            )
        )
    )

    assert response.kind == "TOPIC_CREATE"
    assert response.title == "从 raw 建立 wiki 页面"
    assert response.summary == "Karpathy 提出的核心是让 LLM 持续维护结构化 wiki，而不是只做被动检索。"
    assert response.proposedTopicTitle == "Karpathy的LLM Wiki：为什么个人知识库的终极形态不是RAG，而是一个自维护的Wiki"
    assert response.proposedUnderstanding == "Karpathy 提出的核心是让 LLM 持续维护结构化 wiki，而不是只做被动检索。"
    assert response.proposedClaim == "Karpathy 提出的核心是让 LLM 持续维护结构化 wiki，而不是只做被动检索。"
    assert response.proposedOpenQuestions == "这条新来源应该如何改变当前 wiki 理解？"


def test_agent_runtime_falls_back_to_deterministic_ask_when_provider_invoke_fails(temp_app_env, monkeypatch):
    from inkvault_server import agents
    from inkvault_server.core.config import get_settings

    class FailingStructuredAskLLM:
        def invoke(self, _prompt):
            raise RuntimeError("provider unavailable")

    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def with_structured_output(self, _schema, **_kwargs):
            return FailingStructuredAskLLM()

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    get_settings.cache_clear()
    monkeypatch.setattr(agents, "ChatOpenAI", FakeChatOpenAI)

    runtime = agents.AgentRuntime(get_settings())
    response = runtime.answer(
        agents.AskRequestModel(
            question="这个主题现在最稳定的理解是什么？",
            mode="vault",
            pendingReviewCount=0,
            topic=agents.TopicModel(
                id="topic-001",
                title="Vault-first LLM Wiki",
                currentUnderstanding=["Ask 优先使用 wiki 里的长期知识。"],
                openQuestions=["还缺少哪条最新外部证据？"],
            ),
        )
    )

    assert response.answer == "当前最重要的理解是：Ask 优先使用 wiki 里的长期知识。。接下来优先追问：还缺少哪条最新外部证据？"
    assert response.followUpQuestions == ["还缺少哪条最新外部证据？"]
    assert response.usedWebSources == []


def test_agent_runtime_uses_real_compile_llm_with_structured_provider_when_credentials_present(temp_app_env, monkeypatch):
    from inkvault_server import agents
    from inkvault_server.core.config import get_settings

    captured: dict[str, object] = {"schemas": [], "methods": [], "init_kwargs": []}

    class FakeStructuredCompileLLM:
        def invoke(self, prompt):
            captured["prompt"] = prompt
            return agents.CompileStructuredOutput(
                kind="TOPIC_PATCH",
                title="把 raw 编译进现有 wiki",
                summary="这是由真实 provider 路径生成的 summary。",
                proposedTopicTitle=None,
                proposedUnderstanding="这是更新后的理解。",
                proposedOpenQuestions="下一步应该验证哪条外部来源？",
                proposedClaim="这条 raw 应该更新当前 wiki 的关键结论。",
            )

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured["init_kwargs"].append(kwargs)

        def with_structured_output(self, schema, **kwargs):
            captured["schemas"].append(schema)
            captured["methods"].append(kwargs.get("method"))
            return FakeStructuredCompileLLM()

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("INKVAULT_AGENT_MODEL", "gpt-test")
    monkeypatch.setenv("INKVAULT_AGENT_CONNECT_TIMEOUT_SECONDS", "1.5")
    monkeypatch.setenv("INKVAULT_AGENT_READ_TIMEOUT_SECONDS", "9.0")
    get_settings.cache_clear()
    monkeypatch.setattr(agents, "ChatOpenAI", FakeChatOpenAI)

    runtime = agents.AgentRuntime(get_settings())
    response = runtime.compile(
        agents.CompileRequestModel(
            source=agents.SourceModel(
                id="source-001",
                title="Research-first wiki note",
                kind="WEB",
                excerpt="这是来源摘录。",
                body="这是来源正文。",
                locator="https://example.com/source-001",
                vaultPath="raw/source-001.md",
            ),
            citations=[
                agents.CitationModel(
                    id="chunk-topic-001",
                    title="Vault-first LLM Wiki",
                    kind="TOPIC",
                    excerpt="当前 wiki 的核心理解是把产品中心收回到 raw / ingest / wiki。",
                    locator=None,
                    vaultPath="wiki/vault-first-llm-wiki.md",
                ),
                agents.CitationModel(
                    id="chunk-source-002",
                    title="相关来源摘录",
                    kind="WEB",
                    excerpt="raw 材料需要先沉淀为可审阅的 ingest 提案。",
                    locator="https://example.com/source-002",
                    vaultPath="raw/source-002.md",
                ),
            ],
        )
    )

    assert captured["schemas"] == [
        agents.AskStructuredOutput,
        agents.CompileStructuredOutput,
        agents.AskBriefingStructuredOutput,
    ]
    assert captured["methods"] == ["json_schema", "json_schema", "json_schema"]
    assert captured["init_kwargs"][1] == {
        "model": "gpt-test",
        "api_key": "test-openai-key",
        "base_url": "https://example.com/v1",
        "temperature": 0.1,
        "timeout": (1.5, 9.0),
    }
    assert "Source title: Research-first wiki note" in str(captured["prompt"])
    assert "Retrieved context:" in str(captured["prompt"])
    assert "[chunk-topic-001] Vault-first LLM Wiki" in str(captured["prompt"])
    assert "raw 材料需要先沉淀为可审阅的 ingest 提案。" in str(captured["prompt"])
    assert response.summary == "这是由真实 provider 路径生成的 summary。"
    assert response.proposedClaim == "这条 raw 应该更新当前 wiki 的关键结论。"


def test_agent_runtime_falls_back_to_deterministic_compile_when_provider_invoke_fails(temp_app_env, monkeypatch):
    from inkvault_server import agents
    from inkvault_server.core.config import get_settings

    class FailingStructuredCompileLLM:
        def invoke(self, _prompt):
            raise RuntimeError("provider unavailable")

    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def with_structured_output(self, _schema, **_kwargs):
            return FailingStructuredCompileLLM()

    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    get_settings.cache_clear()
    monkeypatch.setattr(agents, "ChatOpenAI", FakeChatOpenAI)

    runtime = agents.AgentRuntime(get_settings())
    response = runtime.compile(
        agents.CompileRequestModel(
            source=agents.SourceModel(
                id="source-001",
                title="Research-first wiki note",
                kind="WEB",
                excerpt="这是来源摘录。",
                body="这是来源正文。",
                locator="https://example.com/source-001",
                vaultPath="raw/source-001.md",
            )
        )
    )

    assert response.kind == "TOPIC_CREATE"
    assert response.summary == "这是来源摘录。"
    assert response.proposedClaim == "这是来源摘录。"


def test_research_workspace_service_flows_context_and_runtime_metadata_on_real_ask_path(temp_app_env):
    from sqlalchemy import select

    from inkvault_server.agents import AskResponseModel, AskWritebackPackageModel, AskContextTurnModel, WebCitationModel
    from inkvault_server.core.config import get_settings
    from inkvault_server.db import init_db, session_scope
    from inkvault_server.models import AskTurn
    from inkvault_server.research import get_research_service
    from inkvault_server.schemas import AskRequest

    web_source = WebCitationModel(
        url="https://example.com/evidence",
        title="External Evidence",
        excerpt="New context from the web.",
        reasonUsed="It fills a known knowledge gap.",
    )
    writeback_package = AskWritebackPackageModel(
        topicDecision="PATCH",
        targetTopicId="topic-001",
        proposedUnderstanding="The current answer should update the topic summary.",
        proposedClaim="External evidence supports the answer.",
        proposedOpenQuestion="What changed since the previous source snapshot?",
        usedWebSources=[web_source],
    )
    captured_request = None

    init_db()
    with session_scope() as db:
        service = get_research_service(db, get_settings())
        previous_turn = service.ask(AskRequest(question="上一轮问了什么？", mode="vault"))

        def fake_answer(request):
            nonlocal captured_request
            captured_request = request
            return AskResponseModel(
                answer="Grounded answer with external evidence.",
                confidence=0.91,
                followUpQuestions=["What should we verify next?"],
                knowledgeGaps=["We still need one newer source."],
                citationSourceIds=["source-001"],
                usedWebSources=[web_source],
                contextAskTurnIds=["ask-context-1", previous_turn.id],
                canWriteback=False,
                writebackPackage=writeback_package,
            )

        service.agent_runtime.answer = fake_answer
        response = service.ask(
            AskRequest(
                question="延续上一轮，下一步应该补什么证据？",
                mode="vault_plus_web",
                continueFromAskTurnId=previous_turn.id,
            )
        )
        stored_turn = db.scalar(select(AskTurn).where(AskTurn.id == response.id))

        assert captured_request is not None
        assert captured_request.continueFromAskTurnId == previous_turn.id
        assert captured_request.contextTurns == [
            AskContextTurnModel(
                askTurnId=previous_turn.id,
                question=previous_turn.question,
                answer=previous_turn.answer,
            )
        ]
        assert [item.model_dump() for item in response.usedWebSources] == [web_source.model_dump()]
        assert response.contextAskTurnIds == [previous_turn.id]
    assert response.canWriteback is False
    assert stored_turn is not None
    assert stored_turn.parent_ask_turn_id == previous_turn.id
    assert service.decode_web_citations(stored_turn.used_web_sources_json) == [web_source]
    assert service.decode_writeback_package(stored_turn.writeback_package_json) == writeback_package
    assert service.decode_ask_briefing(stored_turn.judgment_payload_json) is not None


def test_research_workspace_service_falls_back_to_persisted_context_ids_when_runtime_returns_only_fabricated_ids(temp_app_env):
    from inkvault_server.agents import AskResponseModel
    from inkvault_server.core.config import get_settings
    from inkvault_server.db import init_db, session_scope
    from inkvault_server.research import get_research_service
    from inkvault_server.schemas import AskRequest

    init_db()
    with session_scope() as db:
        service = get_research_service(db, get_settings())
        previous_turn = service.ask(AskRequest(question="上一轮问了什么？", mode="vault"))

        def fake_answer(_request):
            return AskResponseModel(
                answer="Grounded answer without stable runtime context IDs.",
                confidence=0.82,
                followUpQuestions=["下一步还缺哪条证据？"],
                knowledgeGaps=["还需要补更多背景资料。"],
                citationSourceIds=[],
                usedWebSources=[],
                contextAskTurnIds=["ask-fabricated-only"],
                canWriteback=True,
                writebackPackage=None,
            )

        service.agent_runtime.answer = fake_answer
        response = service.ask(
            AskRequest(
                question="延续上一轮继续追问",
                mode="vault",
                continueFromAskTurnId=previous_turn.id,
            )
        )

        assert response.contextAskTurnIds == [previous_turn.id]


def test_research_workspace_service_materializes_web_sources_and_reuses_persisted_writeback_package(temp_app_env):
    from sqlalchemy import select

    from inkvault_server.agents import AskResponseModel, AskWritebackPackageModel, WebCitationModel
    from inkvault_server.core.config import get_settings
    from inkvault_server.db import init_db, session_scope
    from inkvault_server.models import Source
    from inkvault_server.research import get_research_service
    from inkvault_server.schemas import AskRequest

    web_source = WebCitationModel(
        url="https://example.com/web-evidence",
        title="External Web Evidence",
        excerpt="This external source adds missing context.",
        reasonUsed="It fills a vault knowledge gap.",
    )
    writeback_package = AskWritebackPackageModel(
        topicDecision="CREATE",
        proposedTopicTitle="外部补料主题",
        proposedUnderstanding="应该把这条外部证据沉淀成新的 wiki 理解。",
        proposedClaim="外部网页补足了原先 vault 里缺失的证据。",
        proposedOpenQuestion="这条网页的后续变化需要怎样跟踪？",
        usedWebSources=[web_source],
    )

    init_db()
    with session_scope() as db:
        service = get_research_service(db, get_settings())

        def fake_answer(_request):
            return AskResponseModel(
                answer="这是当前 Ask 的长答案，不应该直接替代 writeback package 里的编译字段。",
                confidence=0.88,
                followUpQuestions=["下一步还要跟踪哪些变化？"],
                knowledgeGaps=["还缺少更多外部时间线来源。"],
                citationSourceIds=[],
                usedWebSources=[web_source],
                contextAskTurnIds=[],
                canWriteback=True,
                writebackPackage=writeback_package,
            )

        service.agent_runtime.answer = fake_answer
        ask_turn = service.ask(AskRequest(question="需要外部网页补料", mode="vault_plus_web"))
        before_sources = db.scalars(select(Source).where(Source.locator == web_source.url)).all()

        first_review = service.create_ask_writeback_proposal(ask_turn.id)
        second_review = service.create_ask_writeback_proposal(ask_turn.id)
        materialized_sources = db.scalars(select(Source).where(Source.locator == web_source.url)).all()

        assert before_sources == []
        assert len(materialized_sources) == 1
        assert materialized_sources[0].vault_path is not None
        assert service.vault_service.exists(materialized_sources[0].vault_path)
        assert first_review.id == second_review.id
        assert first_review.sourceId == materialized_sources[0].id
        assert first_review.proposedUnderstanding == writeback_package.proposedUnderstanding
        assert first_review.proposedClaim == writeback_package.proposedClaim


def test_research_workspace_service_passes_compile_retrieval_context_to_runtime(temp_app_env):
    from inkvault_server.agents import CompileResponseModel
    from inkvault_server.core.config import get_settings
    from inkvault_server.db import init_db, session_scope
    from inkvault_server.research import get_research_service

    captured_request = None

    init_db()
    with session_scope() as db:
        service = get_research_service(db, get_settings())
        first_review = service.get_review_items()[0]
        topic_id = service.accept_review(first_review.id).topicId

        def fake_compile(request):
            nonlocal captured_request
            captured_request = request
            return CompileResponseModel(
                kind="TOPIC_PATCH",
                title="把 raw 编译进现有 wiki",
                summary="把补充材料编译进现有 wiki。",
                proposedTopicTitle=None,
                proposedUnderstanding="补充材料强化了 raw / ingest / wiki 的研究闭环。",
                proposedOpenQuestions="还缺少哪条外部对照来源？",
                proposedClaim="新的 raw 材料支持现有 wiki 主题。",
            )

        service.agent_runtime.compile = fake_compile
        service.create_source(
            "TEXT",
            "外部策略补料 002",
            None,
            "新的材料强调产品应该聚焦 raw、ingest、wiki 的研究闭环。",
            "补料进一步说明，系统的核心工作是导入网页、PDF 与旧笔记，再通过 ingest 转成可审阅的 wiki 记忆。",
        )

        assert captured_request is not None
        assert captured_request.matchedTopic is not None
        assert captured_request.matchedTopic.id == topic_id
        assert captured_request.citations
        assert any(citation.title == captured_request.matchedTopic.title for citation in captured_request.citations)
