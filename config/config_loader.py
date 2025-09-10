import json


def get_config_with_name(name):
    config_file = f"config/keplergl_config/{name}.json"
    with open(config_file, "r") as f:
        config = json.loads(f.read())
    return config

def update_map_style(
    config,
    map_name,
    custom_map_token=None,
    custom_map_icon=None,
    custom_map_url=None,
    set_as_default=False,
):
    if custom_map_token and custom_map_url:
        map_style_id = f"custom_{map_name}"
        config["config"]["mapStyle"]["mapStyles"] = config["config"]["mapStyle"].get(
            "mapStyles", {}
        )
        config["config"]["mapStyle"]["mapStyles"][map_style_id] = {
            "accessToken": custom_map_token,
            "custom": True,
            "icon": custom_map_icon,
            "id": map_style_id,
            "label": map_style_id,
            "url": custom_map_url,
        }

        if set_as_default:
            config["config"]["mapStyle"]["styleType"] = map_style_id
    return config
