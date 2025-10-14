import os
import sys
import requests
import binaryninja
import re

# Plugin details
plugin_name = 'native-predicate-solver'
plugin_filename_base = 'NativePredicateSolver'

# Repository details
repo_owner = 'ScriptWare-Software'
repo_name = 'native-predicate-solver'

def get_latest_release_info():
    api_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest'
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

def parse_binary_filename(filename, extension):
    pattern = rf'^{plugin_filename_base}-(.+)\.{extension}$'
    match = re.match(pattern, filename)
    if match:
        return match.group(1)
    return None

def find_compatible_binary(release_data, platform_extension):
    current_version = binaryninja.core_version().split()[0].split('-')[0]
    is_dev = '-dev' in binaryninja.core_version()

    assets = release_data.get('assets', [])

    exact_match = None
    dev_match = None

    for asset in assets:
        filename = asset['name']
        version = parse_binary_filename(filename, platform_extension)

        if version:
            if version == 'dev' and is_dev:
                dev_match = asset
            elif version == current_version:
                exact_match = asset
                break

    if exact_match:
        return exact_match
    elif dev_match and is_dev:
        return dev_match

    return None

# Function that determines whether native_plugins_data folder exists
def data_folder_exists():
    return os.path.isdir(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data'))

# Function that determines whether current_native_plugin_data file exists
def data_file_exists():
    return os.path.isfile(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data'))

# Function that determines whether temp folder exists
def temp_folder_exists():
    return os.path.isdir(os.path.join(binaryninja.user_plugin_path(), 'temp'))

# Function that reads current_native_plugin_data file
def read_data_file():
    with open(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data'), 'r') as f:
        return f.read().splitlines()
    
# Function that writes to current_native_plugin_data file
def write_data_file(version, hash, file_name):
    with open(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data'), 'w') as f:
        f.write(version + '\n' + hash + '\n' + file_name)

# Function that deletes file from current_native_plugin_data
def delete_data_file():
    path = os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data', plugin_name + '.data')
    if os.path.isfile(path):
        try:
            os.remove(path)
        except Exception as error:
            return path
    return True

# Function that calculates hash of file
def calculate_hash(file_path):
    import hashlib
    hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)
    return hash.hexdigest()

# Function that downloads file
def download_file(file_url, file_name):
    response = requests.get(file_url)
    if response.status_code == 200:
        with open(os.path.join(binaryninja.user_plugin_path(), file_name), 'wb') as f:
            f.write(response.content)
        return True
    else:
        return False
    
# Function that downloads file to temp directory
def download_file_to_temp(file_url, file_name):
    response = requests.get(file_url)
    if response.status_code == 200:
        with open(os.path.join(binaryninja.user_plugin_path(), 'temp', file_name), 'wb') as f:
            f.write(response.content)
        return True
    else:
        return False

# Function that deletes file
def delete_file(file_path):
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except Exception as error:
            return file_path
    return True

# Function that deletes file from temp directory
def delete_file_from_temp(file_name):
    path = os.path.join(binaryninja.user_plugin_path(), 'temp', file_name)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except Exception as error:
            return path
    return True

# Function that determines whether plugin is installed (for current Binary Ninja version)
def is_plugin_installed(file_name):
    return os.path.isfile(os.path.join(binaryninja.user_plugin_path(), file_name))

# Function that alerts user
def alert_user(description):
    binaryninja.interaction.show_message_box('{} (Native plugin loader)'.format(plugin_name), description, binaryninja.enums.MessageBoxButtonSet.OKButtonSet, binaryninja.enums.MessageBoxIcon.InformationIcon)

# Function that does the actual work
def check_for_updates():
    platform = sys.platform.lower()

    if platform.startswith('win'):
        platform_ext = 'dll'
    elif platform.startswith('linux'):
        platform_ext = 'so'
    elif platform.startswith('darwin'):
        platform_ext = 'dylib'
    else:
        alert_user('Unsupported platform')
        return

    release_data = get_latest_release_info()
    if not release_data:
        alert_user('Failed to fetch release information from GitHub')
        return

    latest_version = release_data.get('tag_name', 'Unknown')

    compatible_asset = find_compatible_binary(release_data, platform_ext)
    if not compatible_asset:
        current_version = binaryninja.core_version().split()[0]
        alert_user(f'No compatible binary found for Binary Ninja version {current_version}')
        return

    file = compatible_asset['name']
    file_url = compatible_asset['browser_download_url']

    # Make sure we have data folder
    if not data_folder_exists():
        os.mkdir(os.path.join(binaryninja.user_plugin_path(), 'native_plugins_data'))

    # Make sure we have temp folder
    if not temp_folder_exists():
        os.mkdir(os.path.join(binaryninja.user_plugin_path(), 'temp'))
    else:
        # Delete all files in temp folder
        for file in os.listdir(os.path.join(binaryninja.user_plugin_path(), 'temp')):
            ret = delete_file_from_temp(file)
            if ret != True:
                alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                return

    # Verify we have correct file
    if file and latest_version:
        plugin_data = (read_data_file() if data_file_exists() else None) if data_folder_exists() else None
        # Check if we have all required data (version, hash, file name)
        if plugin_data == None or len(plugin_data) != 3 or plugin_data[0] == None or plugin_data[1] == None or plugin_data[2] == None:
            ret = delete_data_file() if data_file_exists() else True
            if ret != True:
                alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                return
            plugin_data = None

        data_version = plugin_data[0] if plugin_data != None else None
        data_hash = plugin_data[1] if plugin_data != None else None
        data_file_name = plugin_data[2] if plugin_data != None else None

        # Check if we there is a binary for different Binary Ninja version
        if (data_file_name != None and data_file_name != file):
            # Delete old file
            ret = delete_file(os.path.join(binaryninja.user_plugin_path(), data_file_name))
            if ret != True:
                alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                return
            # Delete data file
            ret = delete_data_file()
            if ret != True:
                alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                return
            # Reset data
            plugin_data = None
            data_version = None
            data_hash = None
            data_file_name = None

        if not is_plugin_installed(file):
            # Plugin not installed, just download it
            if download_file(file_url, file):
                # Register plugin in data directory
                write_data_file(latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)), file)
                alert_user('Plugin downloaded successfully, please restart Binary Ninja to load it')
            else:
                alert_user('Failed to download plugin')
        else:
            # Plugin installed, no data about the plugin
            if (data_version == None and data_hash == None):
                # Download latest version of the plugin and check if we have that version
                download_file_to_temp(file_url, file)
                if (calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)) == calculate_hash(os.path.join(binaryninja.user_plugin_path(), 'temp', file))):
                    # We have the latest version, register it in data directory
                    write_data_file(latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)), file)
                    ret = delete_file_from_temp(file)
                    if ret != True:
                        alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                        return
                else:
                    # We don't have the latest version, alert user
                    alert_user('You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
            # Plugin installed, but data shows it's outdated
            elif (data_version != latest_version):
                # Make sure the version in the data directory is actually the version we have installed (we compare hashes - hash now and hash when we downloaded the plugin)
                if (data_hash == calculate_hash(os.path.join(binaryninja.user_plugin_path(), file))):
                    # Yep, version noted in data corresponds to the hash of currently installed plugin
                    alert_user('You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
                else:
                    # Nope, version noted in data doesn't correspond to the hash of currently installed plugin (user probably replaced the plugin)
                    ret = delete_data_file()
                    if ret != True:
                        alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                        return
                    # Download latest version of the plugin and check if we have that version
                    download_file_to_temp(file_url, file)
                    if (calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)) == calculate_hash(os.path.join(binaryninja.user_plugin_path(), 'temp', file))):
                        # We have the latest version, register it in data directory so user is not prompted to update as he probably already did
                        write_data_file(latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)), file)
                        delete_file_from_temp(file)
                    else:
                        # We don't have the latest version, alert user
                        alert_user('You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
            # Plugin installed, data shows it's up to date, but let's make sure
            elif (data_version == latest_version):
                # Make sure the version in the data directory is actually the version we have installed (we compare hashes - hash now and hash when we downloaded the plugin)
                if (data_hash != calculate_hash(os.path.join(binaryninja.user_plugin_path(), file))):
                    # Nope, hash noted in data doesn't correspond to the hash of currently installed plugin (user probably replaced the plugin with different version)
                    ret = delete_data_file()
                    if ret != True:
                        alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                        return
                    # Let's check if our plugin matches the hash in the latest github release (developer could have replaced file in the github release and user updated to it)
                    download_file_to_temp(file_url, file)
                    if (calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)) == calculate_hash(os.path.join(binaryninja.user_plugin_path(), 'temp', file))):
                        # Yep, hash of the plugin in the github release corresponds to the hash of currently installed plugin so we have the latest one
                        write_data_file(latest_version, calculate_hash(os.path.join(binaryninja.user_plugin_path(), file)), file)
                        ret = delete_file_from_temp(file)
                        if ret != True:
                            alert_user('Failed to delete {}, please close Binary Ninja and delete the file/folder manually'.format(ret))
                            return
                    else:
                        # Not the latest one (according to the hash in the github release), but user might be intending to test different version of the plugin, add ignore option
                        alert_user('You are using outdated version of this plugin and it must be updated manually\n1. download the latest version from {}\n2. close Binary Ninja\n3. replace the outdated plugin with the newly downloaded file in {}'.format(file_url, binaryninja.user_plugin_path()))
    else:
        alert_user('This plugin is not supported on current platform or plugin not found or its github releases not found')

class Updater(binaryninja.BackgroundTaskThread):
    def __init__(self):
        binaryninja.BackgroundTaskThread.__init__(self, 'Native plugin loader - checking for updates on: {}'.format(plugin_name), True)

    def run(self):
        check_for_updates()

obj = Updater()
obj.start()
