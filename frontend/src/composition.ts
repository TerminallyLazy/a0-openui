// Original examples for our shipped contract, not the demos' distinct schemas.
// Syntax fixtures only: replace all sample facts and URLs in actual answers.
export const compositionRules = [
  'Compose a coherent answer: a clear takeaway, a primary visual or control, then supporting detail. Match the requested depth. Avoid empty showcase sections, repeated prose, fake live labels and decorative metrics.',
  'For image search and visual recommendations, use ImageCarousel to browse or ImageGrid to compare. Keep the same field order and level of detail in each result; use real image/source URLs, descriptive alt text and useful captions. If no usable image URL exists, use text cards with sources.',
  'For multi-metric reports use Dashboard/DashboardSection, MetricCard and ChartJS. Put a few related MetricCards in a wrapping row (Stack direction row, wrap true) rather than a long vertical column. Label the period, units and data source. Use bar charts for category comparisons, line charts for time series and pie/doughnut only for meaningful parts of a whole. Series must align with labels. Do not imply supplied snapshots refresh automatically.',
  'Use Tabs for alternate views and Accordion for secondary detail. Keep the primary answer visible first. Their children must match the exact signatures below; do not borrow signatures from Material UI, shadcn or other demos.',
  'Use ComparisonTable for the same criteria across options, Agenda/Timeline for plans, KeyValueList for facts and ProgressMeter only when a real denominator is known. Do not invent ratings, prices, dates or availability.',
  'Forms collect only the missing task preferences, typically two to five fields. Use Select/RadioGroup for known choices, DatePicker for dates, and Input/TextArea for free text. Label fields, mark required values and supply Buttons as the second Form argument. Never nest forms. Known editable defaults use literal $variables passed to the control value argument.',
  'Every control must work: local changes use supported bindings; Form submits through @ToAssistant. Do not add fake filtering, pagination, refresh, booking, purchasing or sending controls. Never collect passwords or credentials.',
  'Examples below illustrate syntax and layout only. Replace their sample data, labels and URLs with the actual user/tool facts. Do not reuse example recommendations, sources or totals as evidence.',
];

export const compositionExamples = [
  {
    name: 'Sourced visual results',
    source: `root = Stack([TextContent("Two supplied photo candidates", "large-heavy"), ImageCarousel("Compare the photographs", photos), TextContent("Compare the framing, then open the original source for details.")])
photos = [{title:"Candidate A",imageUrl:"https://images.example.com/a.jpg",alt:"Replace with the actual subject of photo A",description:"Replace with a fact from result A",sourceUrl:"https://example.com/a",sourceName:"Source A"},{title:"Candidate B",imageUrl:"https://images.example.com/b.jpg",alt:"Replace with the actual subject of photo B",description:"Replace with a fact from result B",sourceUrl:"https://example.com/b",sourceName:"Source B"}]`,
  },
  {
    name: 'Report with overview and detailed evidence',
    source: `root = Stack([Dashboard("Three-day progress", "Illustrative supplied snapshot, Monday to Wednesday. Units: completed tasks.", [summary, views], "one")])
summary = DashboardSection("42 tasks completed", [MetricCard("Completed", "42", "10 + 14 + 18 tasks"), ProgressMeter("Target progress", 42, 50, "8 tasks remain against the supplied target")])
views = Tabs([TabItem("trend", "Daily trend", [chart, TextContent("Daily completions increased from 10 to 18.")]), TabItem("details", "Source figures", [table])])
chart = ChartJS("Completed tasks per day", "bar", ["Monday", "Tuesday", "Wednesday"], [{label:"Tasks",data:[10,14,18]}], false, false, "Illustrative values supplied for this example.")
table = Table([Col("Day", ["Monday", "Tuesday", "Wednesday"]), Col("Completed tasks", [10,14,18], "number")])`,
  },
  {
    name: 'Missing preferences with a known editable default',
    source: `root = Stack([TextContent("Tailor the plan", "large-heavy"), TextContent("Your three-person group is filled in. Add the remaining preferences to continue."), form])
$people = "3"
form = Form("trip_preferences", Buttons([Button("Plan with these preferences", @ToAssistant("Use these preferences to plan my trip"))]), [group, pace, interests])
group = FormControl("People", Input("people", "Group size", "number", {required:true,numeric:true,min:1,max:30}, $people))
pace = FormControl("Pace", Select("pace", [SelectItem("relaxed", "Relaxed"), SelectItem("active", "Active")], "Choose a pace", {required:true}))
interests = FormControl("Interests", TextArea("interests", "What would you enjoy?", 3), "Optional; leave blank if you have no preference")`,
  },
  {
    name: 'Comparison with a clear tradeoff and secondary detail',
    source: `root = Stack([TextContent("Choose the workshop format", "large-heavy"), TextContent("In this illustrative brief, the short session suits orientation; the longer session includes practice."), comparison, details, Buttons([Button("Help me choose", @ToAssistant("Help me choose a workshop format using my constraints"))])])
comparison = ComparisonTable("Supplied options", ["Orientation", "Hands-on"], [{label:"Duration",values:["30 minutes","90 minutes"]},{label:"Format",values:["Overview and questions","Overview, practice and questions"]}])
details = Accordion([AccordionItem("scope", "What these options include", [TextContent("These are illustrative options from a supplied brief. Scheduling and availability are not confirmed.")])])`,
  },
];
