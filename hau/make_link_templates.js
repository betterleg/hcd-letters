/**
 * Builds the three "link" query templates (statutory references, keywords, housing laws per
 * letter) from hau_template.json. Run after re-capturing hau_template.json:
 *   node make_link_templates.js
 * These fields are filter-only on HCD's dashboard, so there is no visual to capture; the queries
 * pair each letter's Task ID with the filter table's Value, using the main template's report IDs.
 */
const fs = require('fs');
const main = JSON.parse(fs.readFileSync('hau_template.json', 'utf8'));
const LINKS = [
  ['statutes', 'Statute', 's', 'statute'],
  ['keywords', 'Keyword', 'k', 'keyword'],
  ['laws', 'Authority', 'a', 'housing_law'],
];
for (const [name, entity, alias, label] of LINKS) {
  const body = JSON.parse(JSON.stringify(main.body));
  const q = body.queries[0];
  delete q.CacheKey;
  const cmd = q.Query.Commands[0].SemanticQueryDataShapeCommand;
  cmd.Query = {
    Version: 2,
    From: [{ Name: 'q', Entity: 'Source', Type: 0 }, { Name: alias, Entity: entity, Type: 0 }],
    Select: [
      { Column: { Expression: { SourceRef: { Source: 'q' } }, Property: 'task_effective_number_display_value' }, Name: 'Source.task_effective_number_display_value', NativeReferenceName: 'Task' },
      { Column: { Expression: { SourceRef: { Source: alias } }, Property: 'Value' }, Name: `${entity}.Value`, NativeReferenceName: label },
    ],
    OrderBy: [{ Direction: 1, Expression: { Column: { Expression: { SourceRef: { Source: 'q' } }, Property: 'task_effective_number_display_value' } } }],
  };
  cmd.Binding = { Primary: { Groupings: [{ Projections: [0, 1] }] }, DataReduction: { DataVolume: 3, Primary: { Window: { Count: 500 } } }, Version: 1 };
  const tpl = { ...main, report: `HCD HAU letters dashboard - ${entity} values per letter (filter-only field)`, labels: ['Task', label], body };
  fs.writeFileSync(`hau_${name}_template.json`, JSON.stringify(tpl, null, 2));
  console.log(`wrote hau_${name}_template.json`);
}
