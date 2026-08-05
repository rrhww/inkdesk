import { redirect } from 'next/navigation';

export default function RootPage() {
  // Knowledge is the product entry; the graph remains an exploration view.
  redirect('/app/wiki');
}
