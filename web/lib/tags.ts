import { getKnowledgeSummariesByIds, mockInkdeskDataSource } from "@/lib/mock-data-source";

export function getTagRecords() {
  return mockInkdeskDataSource.getTagRecords();
}

export function getTagConnections(tagId: string) {
  const tag = getTagRecords().find((record) => record.id === tagId);

  if (!tag) {
    return undefined;
  }

  return {
    tag,
    notes: getKnowledgeSummariesByIds(tag.noteIds)
  };
}
