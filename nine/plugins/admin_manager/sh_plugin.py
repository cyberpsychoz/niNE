from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="admin.manager",
    name="Admin Manager",
    description="Plugin to manage player permissions and assign administrators through a whitelist.",
    author="YourName",
    version="1.0.0",
    dependencies=[],
    load_order=50,
    enabled=True,
)

# Optional function on_plugin_load
def on_plugin_load(context):
    context.logger.info(f"{PLUGIN_INFO.name} loaded!")