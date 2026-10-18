/** Institution filter. Offices and chambers. Not the geography filter. */

export type InstitutionChoice = { key: string; label: string };

export const INSTITUTIONS: InstitutionChoice[] = [{ key: "president", label: "President" }];

export function matchesInstitution(officeKey: string, filter: string | null | undefined): boolean {
  if (!filter) return true;
  return officeKey === filter.trim().toLowerCase();
}
