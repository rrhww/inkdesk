import { redirect } from 'next/navigation';

<<<<<<< HEAD
export default function RootPage() {
  // Knowledge is the product entry; the graph remains an exploration view.
  redirect('/app/wiki');
=======
export const metadata: Metadata = {
  title: "Inkdesk 知识图谱",
  description: "基于本地 Markdown 的研发知识图谱工作台。",
  alternates: {
    canonical: "/"
  },
  openGraph: {
    title: "Inkdesk 知识图谱",
    description: "基于本地 Markdown 的研发知识图谱工作台。",
    type: "website"
  }
};

export default function HomePage() {
  redirect("/app/wiki");
>>>>>>> origin/main
}
