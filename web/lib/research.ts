import {
  getResearchTopicDetailFixture,
  researchDashboardFixture,
  researchSourcesFixture,
  researchTopicSummariesFixture,
  vaultHealthFixture,
} from "@/lib/mock/research-fixtures";
import { fetchInkdeskJson, hasApiBaseUrl, InkdeskApiError } from "@/lib/server-api";
import type {
  HealthResponse,
  ResearchDashboard,
  ResearchSourceRecord,
  ResearchTopicDetail,
  ResearchTopicSummary,
  SkillDetail,
  SkillRegistrySummary,
} from "@/lib/types";

async function withResearchFallback<T>(run: () => Promise<T>, fallback: () => T): Promise<T> {
  if (!hasApiBaseUrl()) {
    return fallback();
  }

  try {
    return await run();
  } catch (error) {
    if (error instanceof InkdeskApiError) {
      throw error;
    }
    return fallback();
  }
}

export async function getResearchDashboard(): Promise<ResearchDashboard> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchDashboard>("/admin/home"),
    () => researchDashboardFixture,
  );
}

export async function getWikiPages(): Promise<ResearchTopicSummary[]> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchTopicSummary[]>("/wiki"),
    () => researchTopicSummariesFixture,
  );
}

export async function getWikiDetail(topicId: string): Promise<ResearchTopicDetail> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchTopicDetail>(`/wiki/${topicId}`),
    () => {
      const topic = getResearchTopicDetailFixture(topicId);
      if (!topic) {
        throw new Error(`Unknown mock topic ${topicId}`);
      }
      return topic;
    },
  );
}

export async function getRawSources(): Promise<ResearchSourceRecord[]> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchSourceRecord[]>("/raw"),
    () => researchSourcesFixture,
  );
}

export async function getVaultHealth(): Promise<HealthResponse> {
  return withResearchFallback(
    () => fetchInkdeskJson<HealthResponse>("/health"),
    () => vaultHealthFixture,
  );
}

export async function getSkills(): Promise<SkillRegistrySummary> {
  return withResearchFallback(
    () => fetchInkdeskJson<SkillRegistrySummary>("/skills"),
    () => ({ total: 0, valid: 0, invalid: 0, byStatus: { draft: 0, active: 0, deprecated: 0 }, skills: [] }),
  );
}

export async function getSkillDetail(skillName: string): Promise<SkillDetail> {
  return fetchInkdeskJson<SkillDetail>(`/skills/${skillName}`);
}
