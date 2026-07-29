import { execFile } from "node:child_process";
import { rm } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";

import { expect, test } from "@playwright/test";

const execFileAsync = promisify(execFile);
const useDockerCli = process.env.INKDESK_E2E_DOCKER_CLI === "true";

test("turns a PRD into a live technical-solution graph node", async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  const repositoryRoot = path.resolve(process.cwd(), "..");
  const serverRoot = path.join(repositoryRoot, "server");
  const prdPath = path.join(repositoryRoot, "examples", "mock-interview-prd.md");
  const artifactPath = path.join(
    serverRoot,
    "vault",
    "wiki",
    "generated",
    "mock-interview-prd-tech-solution.md"
  );
  const composePath = path.join(repositoryRoot, "infra", "docker-compose.local-docker.yml");
  const containerArtifactPath = "/app/inkdesk-vault/wiki/generated/mock-interview-prd-tech-solution.md";

  const removeArtifact = async () => {
    if (useDockerCli) {
      await execFileAsync(
        "docker",
        ["compose", "-f", composePath, "exec", "-T", "local-server", "rm", "-f", containerArtifactPath],
        { cwd: repositoryRoot }
      );
      return;
    }
    await rm(artifactPath, { force: true });
  };

  await removeArtifact();
  if (useDockerCli) {
    await expect
      .poll(async () => {
        const response = await fetch("http://127.0.0.1:8080/api/graph");
        const graph = (await response.json()) as { nodes?: Array<{ id?: string }> };
        return graph.nodes?.some(
          (node) => node.id === "vault:wiki/generated/mock-interview-prd-tech-solution.md"
        );
      })
      .toBe(false);
  }
  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ NODES$/)).toBeVisible({ timeout: 60_000 });
  const sourceNode = page.getByTestId("rf__node-repo:examples/mock-interview-prd.md");
  await expect(sourceNode).toBeVisible({ timeout: 30_000 });

  try {
    const execution = useDockerCli
      ? execFileAsync(
          "docker",
          [
            "compose",
            "-f",
            composePath,
            "exec",
            "-T",
            "local-server",
            "inkdesk",
            "run",
            "tech-solution",
            "--prd",
            "/app/repository/examples/mock-interview-prd.md"
          ],
          { cwd: repositoryRoot, timeout: 90_000 }
        )
      : execFileAsync(
          "python",
          [
            "-m",
            "inkdesk_skill_sdk.cli",
            "run",
            "tech-solution",
            "--prd",
            prdPath,
            "--server",
            "http://127.0.0.1:8080"
          ],
          {
            cwd: serverRoot,
            env: { ...process.env, PYTHONPATH: serverRoot },
            timeout: 90_000
          }
        );

    await expect(sourceNode.locator('[data-state="active"]')).toBeVisible({ timeout: 15_000 });
    const { stdout, stderr } = await execution;
    expect(stderr).toBe("");
    expect(stdout).toContain("Generated:");

    const solutionNode = page.getByTestId(
      "rf__node-vault:wiki/generated/mock-interview-prd-tech-solution.md"
    );
    await expect(solutionNode).toBeVisible({ timeout: 30_000 });
    const dependencyEdge = page.getByRole("button", {
      name: "Edge from vault:wiki/generated/mock-interview-prd-tech-solution.md to repo:examples/mock-interview-prd.md"
    });
    for (let index = 0; index < 10 && (await dependencyEdge.count()) === 0; index += 1) {
      await page.locator(".react-flow__controls-zoomin").click();
    }
    await expect(dependencyEdge).toBeVisible();

    await solutionNode.click();
    const reader = page.locator("aside");
    await expect(reader.getByText("wiki/generated/mock-interview-prd-tech-solution.md", { exact: true })).toBeVisible();
    await expect(
      reader.getByRole("article").getByRole("heading", { name: "智能模拟面试系统 PRD 技术方案", level: 1 })
    ).toBeVisible();
    await expect(reader.getByRole("img", { name: "Mermaid architecture diagram" }).locator("svg")).toBeVisible({
      timeout: 30_000
    });
    await page.screenshot({ path: testInfo.outputPath("mvp-tech-solution-closure.png"), fullPage: true });
  } finally {
    await removeArtifact();
  }
});
