/**
 * Shared predicate that decides whether a navigation item is the active route.
 * Items can opt into "exact match" via `end: true`; otherwise the match uses
 * `pathname.startsWith(\`${item.to}/\`)`, and `activePattern` always wins when
 * present so explicit regex overrides prefix matching.
 */
export function isNavItemActive(
  item: { to: string; end?: boolean; activePattern?: RegExp },
  pathname: string,
): boolean {
  if (item.activePattern?.test(pathname)) return true;
  return item.end ? pathname === item.to : pathname.startsWith(`${item.to}/`);
}
