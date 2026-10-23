from usr.plugins.openui.helpers.config import verify_assets


def install(**kwargs):
    verify_assets()


def pre_update(**kwargs):
    from usr.plugins.openui.helpers.generation import stop
    stop()
    from usr.plugins.openui.helpers.current_answer import stop as stop_previews
    stop_previews()


def uninstall(**kwargs):
    pre_update()
    # Artifacts belong to chat history; preserve them and their plain-text fallbacks.
    # There are no services, credentials, or dependencies installed outside this plugin.
