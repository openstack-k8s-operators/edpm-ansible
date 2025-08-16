import os
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_PATH = "molecule/common"
ROLES_PATH = "roles"
FILE_LOADER = FileSystemLoader(TEMPLATE_PATH)
MOLECULE_TEMPLATES = ["molecule.j2", "collections.j2", "prepare.j2"]
PREPARE_TEST_DEPS = 'Prepare test_deps'
ROLE_PATH_STRING = 'role: ../../../../molecule/common/test_deps'
COLLECTIONS_LIST = ['community.general']
PODMAN_EXCLUDED_ROLES = [
    'edpm_bootstrap',
    'edpm_container_manage',
    'edpm_container_rm',
    'edpm_container_standalone',
    'edpm_hosts_entries',
    'edpm_iscsid',
    'edpm_network_config',
    'edpm_nftables',
    'edpm_nodes_validation',
    'edpm_ssh_known_hosts',
    'edpm_sshd',
    'edpm_telemetry',
    'edpm_timezone',
    'edpm_tuned',
    'env_data',
    'edpm_ddp_package',
    'edpm_module_load',
    'edpm_podman',
    'edpm_derive_pci_device_spec'
]


def to_yaml_filter(data, indent=None):
    return yaml.dump(data, indent=indent)


def merge_dicts(dict1, dict2):
    if isinstance(dict1, dict) and isinstance(dict2, dict):
        merged = dict1.copy()
        for key, value in dict2.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged
    return dict2


def get_prepare_parameters(yaml_data):
    prepare_task = next((task for task in yaml_data if isinstance(task, dict) and task.get('name') == 'Prepare'), None)
    if prepare_task:
        return {k: v for k, v in prepare_task.items() if k in ['hosts', 'become', 'gather_facts']}
    return {}


# Setting the environment for jinja2 templates
env = Environment(loader=FILE_LOADER, autoescape=select_autoescape(['yaml']), trim_blocks=True, lstrip_blocks=True)
env.filters['to_yaml'] = to_yaml_filter

for role in os.listdir(ROLES_PATH):
    role_path = os.path.join(ROLES_PATH, role)
    molecule_path = os.path.join(role_path, "molecule", "default")
    prepare_file = os.path.join(molecule_path, "prepare.yml")
    existing_prepare_content = ""

    if os.path.isfile(prepare_file):
        with open(prepare_file, "r") as f:
            existing_prepare_content = f.read()

    # Iterating over all defined templates to generate the corresponding yml files
    for file in MOLECULE_TEMPLATES:
        out_file = file[:-3] + ".yml"
        template_file = file
        template = env.get_template(template_file)
        render_config = {}

        # Configuring render settings the templates
        if file == 'molecule.j2':
            molecule_file = os.path.join(molecule_path, "molecule.yml")
            if os.path.isfile(molecule_file):
                with open(molecule_file, "r") as f:
                    molecule_data = yaml.safe_load(f)
                render_config = {
                    'dependency': molecule_data.get('dependency', {'name': ''}),
                    'driver': {} if role in PODMAN_EXCLUDED_ROLES else molecule_data.get('driver', {'name': ''}),
                    'platforms': molecule_data.get('platforms', [{'name': '', 'image': ''}]),
                    'provisioner': molecule_data.get('provisioner', {'name': ''}),
                    'verifier': molecule_data.get('verifier', {'name': ''}),
                    'scenario': molecule_data.get('scenario', {'name': ''})
                }
            else:
                render_config = {
                    'dependency': {'name': ''},
                    'driver': {} if role in PODMAN_EXCLUDED_ROLES else {'name': ''},
                    'platforms': [{'name': '', 'image': ''}],
                    'provisioner': {'name': ''},
                    'verifier': {'name': ''},
                    'scenario': {'name': ''}
                }

        if file == 'collections.j2':
            collections_formatted = "\n- ".join(COLLECTIONS_LIST)
            render_config = {"collections": collections_formatted}

        if file == 'prepare.j2':
            if PREPARE_TEST_DEPS in existing_prepare_content or ROLE_PATH_STRING in existing_prepare_content:
                continue
            prepare_params = get_prepare_parameters(yaml.safe_load(existing_prepare_content))
            render_config = {'prepare_params': prepare_params}
            final_content = template.render(render_config).rstrip() + '\n' + existing_prepare_content.rstrip()
        else:
            existing_content = ""
            existing_file = os.path.join(molecule_path, out_file)
            if os.path.isfile(existing_file):
                with open(existing_file, "r") as f:
                    existing_content = f.read()
            final_content = template.render(render_config).rstrip()

            # If content already exists, merge the new data with the existing one
            if existing_content:
                rendered_data = yaml.safe_load(final_content)
                existing_data = yaml.safe_load(existing_content)
                merged_data = merge_dicts(existing_data, rendered_data)
                final_content = yaml.dump(merged_data)

        with open(os.path.join(molecule_path, out_file), "w") as f:
            if out_file in ['collections.yml', 'molecule.yml']:
                f.write('---\n' + final_content.rstrip() + "\n")
            else:
                f.write(final_content.rstrip() + "\n")
