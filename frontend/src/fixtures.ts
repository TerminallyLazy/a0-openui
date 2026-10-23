export const fixtures = {
  dashboard: 'root = Stack([CardHeader("Weekly overview", "Synthetic sample"), MetricIndicatorInline("42", "Completed tasks"), chart, table])\nchart = BarChart(["Mon", "Tue", "Wed"], [Series("Completed", [10, 14, 18])])\ntable = Table([Col("Day", ["Mon", "Tue", "Wed"]), Col("Completed", [10, 14, 18], "number")])',
  form: 'root = Stack([CardHeader("Choose the next step"), form])\nform = Form("request", Buttons([Button("Send request", @ToAssistant("Please help with this request"))]), [FormControl("Request", Input("request", "What should happen next?", "text", {required: true}))])',
  tabs: 'root = Stack([Tabs([TabItem("summary", "Summary", [TextContent("Ready to review")]), TabItem("details", "Details", [TextContent("All values are synthetic.")])])])',
};
