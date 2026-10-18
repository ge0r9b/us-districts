import { databaseUrl } from "../ingest/db.ts";
import { migrate } from "../ingest/migrate.ts";

const result = await migrate(databaseUrl());
console.log(result.applied ? `applied ${result.checksum}` : `already applied ${result.checksum}`);
