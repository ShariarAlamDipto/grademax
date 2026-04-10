import type { Metadata } from "next"
import { pastPaperSubjects } from "@/lib/subjects"
import { PaperHubPage, buildPaperHubMetadata } from "../_hub/PaperHubPage"

export const revalidate = 3600

const PAPER = "1"

export function generateStaticParams() {
  return pastPaperSubjects.map((s) => ({ subject: s.slug }))
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ subject: string }>
}): Promise<Metadata> {
  const { subject } = await params
  return buildPaperHubMetadata(subject, PAPER)
}

export default async function PaperHubPage1({
  params,
}: {
  params: Promise<{ subject: string }>
}) {
  const { subject } = await params
  return <PaperHubPage subject={subject} paperNumber={PAPER} />
}
