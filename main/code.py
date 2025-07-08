import os
from dotenv import load_dotenv
import gradio as gr

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ConnectedAgentTool, MessageRole, ListSortOrder, FileSearchTool, FilePurpose
from azure.identity import DefaultAzureCredential

# Load env variables
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

# Initialize agents client
agents_client = AgentsClient(endpoint=project_endpoint, credential=DefaultAzureCredential())

# Agent instructions
orchestration_agent_name = "orchestrierungs_agent"
orchestration_instructions = """
Du bist der Orchestrator-Agent in einem Multi-Agentensystem für die Planung von Geschäftsreisen.

## Ziel
Koordiniere spezialisierte Agenten, um anhand natürlicher Spracheingaben vollständige, regelkonforme Reisen für Mitarbeitende zu planen und zu buchen.

## Verhalten
- Analysiere Nutzereingaben (z. B. „Ich muss Dienstag bis Freitag nach Berlin“)
- Extrahiere strukturierte Reisedaten (Ziel, Zeitraum, Abflugort, Zeiten, Hotelpräferenz etc.)
- Prüfe Vollständigkeit und Konsistenz der Informationen
- Stelle gezielte Rückfragen bei fehlenden oder widersprüchlichen Angaben
- Orchestriere die Ausführung durch die folgenden Agenten

## Verbundene Agenten
- **Agent 1 Policy_Prüfungs_Agent:** Extrahiere die Rahmenbedingungen für die eingegebene Reise aus der Reiserichtlinie.
- **Agent 2 Recherche_Agent:** Sucht passende Transport- und Unterkunftsoptionen auf Basis der Eingaben und Richtlinien.
- **Agent 3 Buchungs_Agent:** Führt die Buchung durch, sobald eine genehmigte Option vorliegt.

## Fehler- und Iterationslogik
- Falls Agent 2 keine gültigen Optionen findet, frage den Nutzer gezielt nach Alternativen (z. B. andere Uhrzeit, mehr Flexibilität, alternative Hotels).
- Wiederhole den Ablauf nach Anpassung der Parameter.
- Vor finalen Buchung der Reise, frag immer den Nutzer, ob die gefundenen Optionen genehmigt werden sollen.
- Im Falle einer Policy-Verletzung: Informiere den Nutzer, biete ggf. Alternativen an oder leite für Genehmigung weiter.

## Antwortstil
- Kurz, präzise und prozessfokussiert
- Antworte wie ein einsatzbereiter Koordinator: „Ziel erkannt, Zeitraum fehlt – Rückfrage erforderlich.“ oder „Alle Daten vollständig – starte Agent 1.“

## Wichtig
- Reagiere wie ein Agent im Einsatz, nicht wie ein Chatbot.
- Dein Ziel ist es, Entscheidungen anzustoßen, nicht passiv zu warten.
- Folge strikt dem definierten Ablauf, initiiere Folgeaktionen aktiv.
"""

policy_agent_name = "policy_pruefungs_agent"
policy_agent_instructions = """
Du bist der Policy-Prüfungs-Agent. Deine Aufgabe ist es, die Rahmenbedingungen für die eingegebene Reise aus der Reiserichtlinie zu extrahieren und zu prüfen, ob die geplante Reise regelkonform ist. Gib bei Verstößen klare Hinweise.
"""

recherche_agent_name = "reise_recherche_agent"
recherche_agent_instructions = """
Du bist der Recherche-Agent. Suche passende Transport- und Unterkunftsoptionen auf Basis der Nutzereingaben und der von Agent 1 gelieferten Richtlinien. Gib mehrere Optionen zurück, falls möglich.
"""

buchungs_agent_name = "buchungs_agent"
buchungs_agent_instructions = """
Du bist der Buchungs-Agent. Führe die Buchung durch, sobald eine genehmigte Option vorliegt. Bestätige die Buchung und gib eine Zusammenfassung der gebuchten Reise zurück.
"""

def setup_agents():
    global thread, orchestrator_agent, recherche_agent, buchungs_agent, policy_agent

    # Create the Research Agent
    recherche_agent = agents_client.create_agent(
        model=model_deployment,
        name=recherche_agent_name,
        instructions=recherche_agent_instructions
    )


    # Create the Booking Agent
    buchungs_agent = agents_client.create_agent(
        model=model_deployment,
        name=buchungs_agent_name,
        instructions=buchungs_agent_instructions
    )

    
    # Define the path to the file to be uploaded
    policy_file_path = "Resources/Reiserichtlinie_Munich_Agent_Factory_GmbH_v1.pdf"

    # Upload the file to foundry and create a vector store
    file = agents_client.files.upload_and_poll(file_path=policy_file_path, purpose=FilePurpose.AGENTS)
    vector_store = agents_client.vector_stores.create_and_poll(file_ids=[file.id], name="travel_policy_vector_store")

    # Create file search tool with resources followed by creating agent
    file_search = FileSearchTool(vector_store_ids=[vector_store.id])

    # Create the policy agent using the file search tool
    policy_agent = agents_client.create_agent(
        model=model_deployment,
        name=policy_agent_name,
        instructions=policy_agent_instructions,
        tools=file_search.definitions,
        tool_resources=file_search.resources,
    )

    # Create the connected agent tools for all 3 agents
    # Note: The connected agent tools are used to connect the agents to the orchestrator agent
    policy_agent_tool = ConnectedAgentTool(
        id=policy_agent.id,
        name=policy_agent_name,
        description="Prüft die Reiserichtlinie für die geplante Reise."
    )
    
    recherche_agent_tool = ConnectedAgentTool(
        id=recherche_agent.id,
        name=recherche_agent_name,
        description="Sucht Transport- und Unterkunftsoptionen."
    )

    buchungs_agent_tool = ConnectedAgentTool(
        id=buchungs_agent.id,
        name=buchungs_agent_name,
        description="Bucht genehmigte Reiseoptionen."
    )

    # Create the Orchestrator Agent
    # This agent will coordinate the other agents based on user input
    orchestrator_agent = agents_client.create_agent(
        model=model_deployment,
        name=orchestration_agent_name,
        instructions=orchestration_instructions,
        tools=[
            policy_agent_tool.definitions[0],
            recherche_agent_tool.definitions[0],
            buchungs_agent_tool.definitions[0]
        ]
    )

    thread = agents_client.threads.create()

# === Gradio Chat-Callback ===
def azure_enterprise_chat(user_input, chat_history):
    agents_client.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content=user_input,
    )

    run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=orchestrator_agent.id)

    if run.status == "failed":
        return chat_history + [[user_input, f"Fehler: {run.last_error}"]], user_input

    messages = list(agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING))

    latest_response = ""
    for message in reversed(messages):
        if message.role == MessageRole.AGENT and message.text_messages:
            latest_response = message.text_messages[-1].text.value
            break

    return chat_history + [{"role": "user", "content": user_input}, {"role": "assistant", "content": latest_response}], user_input

def clear_thread():
    global thread
    thread = agents_client.threads.create()
    return []

# === Gradio Theme Setup ===
brand_theme = gr.themes.Default(
    primary_hue="teal",
    secondary_hue="gray",
    neutral_hue="slate",
    font=["Inter", "Segoe UI", "sans-serif"],
    font_mono=["Fira Code", "monospace"],
    text_size="md",
).set(
    button_primary_background_fill="#0f766e",                     # Teal
    button_primary_background_fill_hover="#115e59",
    button_primary_background_fill_hover_dark="#0d9488",
    button_primary_background_fill_dark="#0d9488",
    button_primary_text_color="#ffffff",

    button_secondary_background_fill="#334155",                   # Slate
    button_secondary_background_fill_hover="#475569",
    button_secondary_background_fill_hover_dark="#1e293b",
    button_secondary_text_color="#e2e8f0",                        # Light slate

    body_background_fill="#0f172a",                               # Deep navy
    block_background_fill="#1e293b",                              # Slightly lighter for contrast
    body_text_color="#e2e8f0",                                    # Light slate text
    body_text_color_subdued="#94a3b8",                            # Muted slate

    block_border_color="#334155",
    block_border_color_dark="#1e293b",

    input_background_fill="#0f172a",                              # Match body for seamless input
    input_border_color="#334155",
    input_border_color_focus="#14b8a6",                           # Teal accent
)


# === Gradio UI ===
with gr.Blocks( css="footer {visibility: hidden;}", fill_height=True) as demo:

    gr.HTML("<h1 style=\"text-align: center;\">Resebuchungs Agent</h1>")

    chatbot = gr.Chatbot(
        type="messages",
        examples=[
            {"text": "Ich muss Dienstag bis Freitag nach Berlin reisen."},
            {"text": "Bitte buche mir ein Hotel in Frankfurt ab Mittwoch."},
        ],
        show_label=False,
        scale=1,
    )

    textbox = gr.Textbox(
        show_label=False,
        lines=1,
        submit_btn=True,
        placeholder="Beschreibe deine Geschäftsreise...",
    )

    def on_example_clicked(evt: gr.SelectData):
        return evt.value["text"]

    chatbot.example_select(fn=on_example_clicked, inputs=None, outputs=textbox)

    (textbox
     .submit(
         fn=azure_enterprise_chat,
         inputs=[textbox, chatbot],
         outputs=[chatbot, textbox],
     )
     .then(
         fn=lambda: "",
         outputs=textbox,
     )
    )

    chatbot.clear(fn=clear_thread, outputs=chatbot)

# === App Launch ===
if __name__ == "__main__":
    with agents_client:
        setup_agents()
        demo.launch(share=True)

        # Optional cleanup (if needed)
        agents_client.delete_agent(orchestrator_agent.id)
        agents_client.delete_agent(buchungs_agent.id)