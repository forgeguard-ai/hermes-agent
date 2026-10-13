/** Two provider ids name the same main endpoint when they are equal, or when
 * one is the bare runtime id ``custom`` and the other a named ``custom:<name>``
 * slug: an agent built from config reports the first, the model picker the
 * second, for the same configured endpoint. Two different named slugs are
 * different endpoints. */
export function sameMainProvider(a: string, b: string): boolean {
  if (a === b) return true;
  return (
    (a === "custom" && b.startsWith("custom:")) ||
    (b === "custom" && a.startsWith("custom:"))
  );
}
