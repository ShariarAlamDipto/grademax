/**
 * Which parts of /admin a teacher may use.
 *
 * The admin panel is admin-only except for these prefixes, which teachers
 * share. The admin layout reads the request path from the `x-pathname` header
 * that src/proxy.ts sets on every request, since a server layout is not given
 * its own pathname.
 */
export const TEACHER_ADMIN_PREFIXES = ["/admin/workbook"] as const

/** Where a teacher lands when they open /admin itself. */
export const TEACHER_ADMIN_HOME = "/admin/workbook/verify"

export const PATHNAME_HEADER = "x-pathname"

export function isTeacherAdminPath(pathname: string | null | undefined): boolean {
  if (!pathname) return false
  return TEACHER_ADMIN_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))
}
