import { NextResponse } from "next/server";

import { getVaultPreviewDocument } from "@/lib/vault-preview";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;

  try {
    return NextResponse.json(await getVaultPreviewDocument(documentId));
  } catch {
    return NextResponse.json({ message: "Preview document not found." }, { status: 404 });
  }
}
