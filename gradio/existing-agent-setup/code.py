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

def setup_agents():
    global thread, my_agent

    my_agent = agents_client.get_agent(
        agent_id="asst_Iz30xcOMuDUzr9hZMJsMYffw" # Replace with actual ID of your agent
    )

    thread = agents_client.threads.create()

# === Gradio Chat-Callback ===
def azure_enterprise_chat(user_input, chat_history):
    agents_client.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content=user_input,
    )

    run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=my_agent.id)

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

    gr.HTML(f"<h1 style=\"text-align: center;\">Agent Playground in Gradio</h1>")

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
        placeholder="Chate mit dem Agenten...",
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
        demo.launch()
