import { ToolsStrip } from '@/components/ToolsBanner'

/**
 * The paper viewer (/viewer): the practice-tools strip sits directly under the
 * navbar while a paper is open. The page's own metadata stays in page.tsx.
 */
export default function ViewerLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <ToolsStrip />
      {children}
    </>
  )
}
