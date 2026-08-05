<<<<<<< HEAD
import { redirect } from 'next/navigation';

export default function RootPage() {
  // Knowledge is the product entry; the graph remains an exploration view.
  redirect('/app/wiki');
=======
import { redirect } from "next/navigation";

export default function AppPage() {
  redirect("/app/wiki");
>>>>>>> origin/main
}
