"""Analytics tab."""

from collections.abc import Callable
from dataclasses import dataclass

import gradio as gr

from dashboard.metrics import DashboardData


@dataclass(frozen=True)
class AnalyticsPorts:
    is_configured: Callable[[], bool]
    authenticate: Callable[[str], bool]
    load_data: Callable[..., DashboardData]
    clear_cache: Callable[[], None]
    not_configured_message: str
    count_behavior_failures: Callable[[], int]
    get_behavior_addendum: Callable[[], str]
    regenerate_behavior: Callable[[], str]
    wrong_password_message: str = "Contraseña incorrecta."


def _data_updates(data: DashboardData) -> tuple:
    return (
        data.sessions,
        data.lead_rate,
        data.leads_count,
        data.calls_count,
        data.unknown_rate,
        data.daily,
        data.unknown,
        data.ratings,
    )


def build_analytics_tab(ports: AnalyticsPorts) -> None:
    if not ports.is_configured():
        gr.Markdown(ports.not_configured_message)
        return

    with gr.Column(visible=True) as login_panel:
        gr.Markdown("### Analytics internas")
        gr.Markdown("Acceso restringido.")
        password = gr.Textbox(label="Contraseña", type="password")
        login_error = gr.Markdown("")
        login_btn = gr.Button("Ingresar", variant="primary")

    with gr.Column(visible=False) as dashboard_panel:
        refresh_btn = gr.Button("Actualizar métricas")

        with gr.Row():
            kpi_sessions = gr.Number(label="Sesiones", interactive=False, precision=0)
            kpi_lead_rate = gr.Number(label="Conversión a lead (%)", interactive=False)
            kpi_leads = gr.Number(label="Emails capturados", interactive=False, precision=0)
            kpi_calls = gr.Number(label="Calls agendadas", interactive=False, precision=0)
            kpi_unknown = gr.Number(label="Brechas de perfil (%)", interactive=False)

        daily_plot = gr.LinePlot(
            x="día",
            y="valor",
            color="métrica",
            title="Actividad diaria",
        )
        with gr.Row():
            unknown_plot = gr.BarPlot(x="veces", y="pregunta", title="Top preguntas sin respuesta")
            ratings_plot = gr.BarPlot(x="rating", y="count", title="Distribución de feedback")

        with gr.Accordion("Aprendizaje de comportamiento", open=False):
            gr.Markdown(
                "Reglas generadas cuando el evaluator agota los 3 reintentos. "
                "Se agregan al system prompt sin modificar summary ni LinkedIn."
            )
            failure_count = gr.Number(
                label="Turnos con 3 reintentos fallidos",
                interactive=False,
                precision=0,
            )
            regenerate_btn = gr.Button("Regenerar ajustes de comportamiento")
            behavior_addendum = gr.Textbox(
                label="Ajustes activos en el system prompt",
                lines=12,
                interactive=False,
            )

    metric_outputs = [
        kpi_sessions,
        kpi_lead_rate,
        kpi_leads,
        kpi_calls,
        kpi_unknown,
        daily_plot,
        unknown_plot,
        ratings_plot,
    ]
    behavior_outputs = [failure_count, behavior_addendum]

    def _behavior_state():
        return ports.count_behavior_failures(), ports.get_behavior_addendum()

    def _login(entered_password: str):
        if not ports.authenticate(entered_password):
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                ports.wrong_password_message,
                *[gr.update() for _ in metric_outputs],
                *[gr.update() for _ in behavior_outputs],
            )
        return (
            gr.update(visible=False),
            gr.update(visible=True),
            "",
            *_data_updates(ports.load_data()),
            *_behavior_state(),
        )

    def _refresh():
        ports.clear_cache()
        return _data_updates(ports.load_data(force=True))

    def _regenerate_behavior():
        addendum = ports.regenerate_behavior()
        return ports.count_behavior_failures(), addendum

    login_targets = [login_panel, dashboard_panel, login_error, *metric_outputs, *behavior_outputs]
    login_btn.click(_login, inputs=[password], outputs=login_targets)
    password.submit(_login, inputs=[password], outputs=login_targets)
    refresh_btn.click(_refresh, outputs=metric_outputs)
    regenerate_btn.click(_regenerate_behavior, outputs=behavior_outputs)
