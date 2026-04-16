import { TagsOverview } from "@/components/workbench/tags-overview";
import { getTagRecords } from "@/lib/tags";

export default function TagsPage() {
  return <TagsOverview tags={getTagRecords()} />;
}
