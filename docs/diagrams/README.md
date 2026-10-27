# ProjectForge UML class diagram

Open ProjectForge_UML_Class_Diagram_A4.drawio in draw.io / diagrams.net using File > Open From > Device. The .xml file contains the same uncompressed mxGraph XML and can also be opened. Use the three page tabs at the bottom to switch views.

The file uses A4 landscape pages (297 x 210 mm), Times New Roman, approximately 16-point titles and 12-point class text at 100% print scale. Captions correspond to Section 2.3 of the supplied report index. If the report must remain portrait throughout, insert each diagram on a landscape section page or request a portrait re-layout; shrinking a landscape page into a portrait text column will reduce readability.

Each UML class uses name, attributes, and operations compartments. + denotes a public member; - denotes a private-by-convention member. Method parameters and type annotations are shortened for readability. Selected classes and relationships are shown, not every implementation detail.

Views:

1. Project data and specification classes.
2. The six specialists, execution harness, and model providers.
3. Source generation, task scheduling, controlled files, and isolated verification.

Notation matches the supplied UML examples: composition uses a filled diamond at the owner, aggregation a hollow diamond at the holder, dependency a dashed open arrow, directed association a solid open arrow, and inheritance a solid line with a hollow triangle toward the parent. Realization is intentionally not added: no declared model-client interface or specialist superclass exists in the inspected code. The providers are alternative implementations selected by configuration; they do not inherit from each other.

ProjectContext stores its build_spec as a serialized dictionary; its association with BuildSpec depicts the represented data schema, not an in-memory typed BuildSpec field. Pydantic model inheritance is illustrated by ProjectState; the note on page 1 also identifies other Pydantic models. Composition of structured requirements/files denotes nested payload ownership; these are not separate SQLite tables. TaskScheduler and AgentToolContext hold externally supplied collaborators, represented by hollow diamonds. Agent-to-harness composition represents a separate instance per agent.

The report-ready PDF uses the same geometry as the editable XML. XML references and page boundaries were checked programmatically, and page previews were visually inspected. The XML was not opened in a live draw.io editor during creation; open it there before final report export to confirm the editor's text metrics and printer settings.

Implementation references:

- backend/app/models/schemas.py
- backend/app/api/persistence.py
- backend/app/agents/{product,aiml,engineering,ux,security,qa}_agent.py
- backend/app/harness/base_harness.py
- backend/app/agents/model_client.py
- backend/app/execution/spec/{build_spec_models,build_spec_compiler}.py
- backend/app/execution/orchestrator/coding_orchestrator.py
- backend/app/execution/tasks/{task_graph,task_scheduler,task_models}.py
- backend/app/execution/agent/{coding_agent,tools}.py
- backend/app/execution/sandbox/{test_runner,executor}.py
- backend/app/execution/repository/repository_manager.py

The standalone generated NoteKeeper Note class is excluded because this diagram documents ProjectForge, not its generated sample website.
