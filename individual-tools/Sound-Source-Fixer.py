import json


def update_sound_source(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)

    for category in data.get('categories', []):
        for item in category.get('categoryItems', []):
            sound_file = item.get('soundFile', '')

            if '/OAT1/' in sound_file:
                item['soundSource'] = 'Open Alpha Playtest #1'
            elif '/OAT2/' in sound_file:
                item['soundSource'] = 'Open Alpha Playtest #2'

    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)

    print("sounds.json has been updated successfully!")


if __name__ == "__main__":
    update_sound_source('../../HEAT-Labs-Configs/sounds.json')