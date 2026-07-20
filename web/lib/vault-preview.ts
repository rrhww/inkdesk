import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const previewDocuments = {
  "product-roadmap": "product-roadmap.md",
  "system-architecture": "system-architecture.md",
  "tech-decisions": "tech-decisions.md",
  "ai-rd-automation-llm-wiki": "ai-rd-automation-llm-wiki.md"
} as const;

export type VaultPreviewDocument = {
  id: keyof typeof previewDocuments;
  sourcePath: string;
  title: string;
  content: string;
};

export async function getVaultPreviewDocument(documentId: string): Promise<VaultPreviewDocument> {
  if (!(documentId in previewDocuments)) {
    throw new Error("Requested graph document is not available for preview.");
  }

  const id = documentId as keyof typeof previewDocuments;
  const fileName = previewDocuments[id];
  const sourcePath = `server/vault/wiki/${fileName}`;
  const absolutePath = resolve(process.cwd(), "..", sourcePath);
  const content = await readFile(absolutePath, "utf8");
  const title = content.match(/^#\s+(.+)$/m)?.[1] ?? fileName;

  return { id, sourcePath, title, content };
}
