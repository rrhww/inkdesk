import { redirect } from "next/navigation";

type TopicCompatibilityPageProps = {
  params: Promise<{
    id: string;
  }>;
};

export default async function TopicCompatibilityPage({ params }: TopicCompatibilityPageProps) {
  const { id } = await params;
  redirect(`/app/wiki/${id}`);
}
