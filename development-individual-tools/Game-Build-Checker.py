import aiohttp
import asyncio
import hashlib
import os
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import xml.etree.ElementTree as ET

# Game codes display names
game_codes = {
    "CW.WW.PRODUCTION": {
        "cdn": "https://wgus-eu.wargaming.net",
        "display_name": "World of Tanks: HEAT",
    }
}

OUTPUT_JSON_FILE = "../../HEAT-Labs-Configs/game_builds.json"


def format_size(size_value):
    size_bytes = int(size_value)
    if size_bytes < 1024:
        return f"{size_bytes} B"
    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.2f} KB"
    size_mb = size_kb / 1024
    if size_mb < 1024:
        return f"{size_mb:.2f} MB"
    size_gb = size_mb / 1024
    return f"{size_gb:.2f} GB"


# Format build size
def format_size_gb(size_bytes):
    if size_bytes == 0:
        return "0 GB"
    size_gb = size_bytes / (1024 * 1024 * 1024)
    return f"{size_gb:.2f} GB"


# Convert version string (YYYYMMDDHHMMSS) to readable date format
def parse_build_date(version_str):
    try:
        if len(version_str) >= 14:
            dt = datetime.strptime(version_str[:14], "%Y%m%d%H%M%S")
            return dt.strftime("%Y.%m.%d %H:%M:%S")
    except ValueError:
        pass
    return version_str  # Return original if parsing fails


async def get_metadata(game_id, cdnUrl):
    # Determine protocol version based on CDN
    protocol_version = "7.6" if "lesta" in cdnUrl else "7.7"
    url = f"{cdnUrl}/api/v1/metadata/?guid={game_id}&chain_id=unknown&protocol_version={protocol_version}"
    print(f"Fetching metadata: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                xml_data = await response.text()
                root = ET.fromstring(xml_data)
                version = (
                    root.find(".//version").text
                    if root.find(".//version") is not None
                    else ""
                )
                build_date = parse_build_date(version)
                final_url = parse_xml(xml_data, cdnUrl, protocol_version)
                return final_url, build_date
    except aiohttp.ClientError as e:
        print(f"Error fetching metadata for {game_id}: {e}")
        return None, None


def extract_filename_from_url(url, display_name):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    game_id = query_params.get("game_id", [None])[0]

    if game_id and display_name:
        return f"{display_name} ({game_id})"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{display_name or 'Unknown'} - {timestamp}"


async def fetch_content(session, url):
    for _ in range(3):
        try:
            async with session.get(url) as response:
                text = await response.text()
                if "<h1>Server Error (500)</h1>" in text:
                    print("There was server error with fetching data")
                    continue
                return text
        except Exception as e:
            print(f"Error during fetch of {url}: {e}")
            return None
    print(f"Three retries of fetching {url} failed")
    return None


def parse_xml(xml_data, cdnUrl, metadata_protocol_version):
    root = ET.fromstring(xml_data)

    version = root.find(".//version").text
    chain_id = root.find(".//chain_id").text
    default_language = root.find(".//default_language").text

    publisher_id = root.get("wgc_publisher_id")
    if publisher_id:
        publisher_id = publisher_id.split(",")[0]

    client_type_node = root.find(".//client_types/client_type[@id='hd']")
    if client_type_node is None:
        client_type_node = root.find(".//client_types")
        default_client_type = client_type_node.get("default")
        client_type_node = root.find(
            f".//client_types/client_type[@id='{default_client_type}']"
        )

    final_app_type_node = client_type_node.find("final_app_type")
    if final_app_type_node is not None and final_app_type_node.text:
        final_app_type = final_app_type_node.text
    else:
        final_app_type = client_type_node.get("id")

    client_parts = client_type_node.findall("client_parts/client_part")
    client_versions = [f"{part.get('id')}_current_version=0" for part in client_parts]

    # Use the metadata protocol version for patches chain as well
    protocol_version = metadata_protocol_version

    final_url = (
        f"{cdnUrl}/api/v1/patches_chain/?"
        f"protocol_version={protocol_version}"
        f"&client_type={final_app_type}"
        f"&lang={default_language}"
        f"&metadata_version={version}"
        f"&metadata_protocol_version={protocol_version}"
        f"&chain_id={chain_id}"
        f"&game_installation=true"
        f"&game_id={root.find('.//app_id').text}"
    )

    if publisher_id:
        final_url += f"&gc_publisher={publisher_id}"

    final_url += f"&{'&'.join(client_versions)}"
    print(f"Generated patches chain URL: {final_url}")
    return final_url


# Process XML data and convert it to JSON
def process_xml_to_json(xml_data, display_name, build_date, version_name, content_hash):
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"XML ParseError: {e}")
        return None

    if root.tag == "error":
        return None

    result = {
        "build_info": {
            "content_hash": content_hash,
            "display_name": display_name,
            "build_date": build_date,
            "version_name": version_name,
            "compressed_size": "0 GB",
            "uncompressed_size": "0 GB",
            "file_count": 0,
        },
        "web_seeds": [],
        "patches": [],
        "delay_preload": False,
    }

    # Process web seeds
    web_seeds = root.find("web_seeds")
    if web_seeds is not None:
        for url_element in web_seeds.findall("url"):
            seed_info = {
                "url": url_element.text.strip() if url_element.text else "",
                "threads": int(url_element.attrib.get("threads", 0)),
                "protocol": url_element.attrib.get("protocol", ""),
            }
            result["web_seeds"].append(seed_info)

    # Process patches
    total_file_count = 0
    total_compressed_size = 0
    total_uncompressed_size = 0

    for patches_chain in root.findall("patches_chain"):
        chain_type = patches_chain.attrib.get("type", "unknown")

        for patch in patches_chain.findall("patch"):
            part = (
                patch.find("part").text if patch.find("part") is not None else "unknown"
            )
            version_to = (
                patch.find("version_to").text
                if patch.find("version_to") is not None
                else "unknown"
            )

            patch_info = {
                "chain_type": chain_type,
                "part": part,
                "version_to": version_to,
                "files": [],
            }

            # Process files in this patch
            for file in patch.findall(".//file"):
                file_name = (
                    file.find("name").text if file.find("name") is not None else ""
                )
                package = file_name.split("/")[-1] if file_name else ""

                size_value = (
                    file.find("size").text if file.find("size") is not None else None
                )
                unpacked_value = (
                    file.find("unpacked_size").text
                    if file.find("unpacked_size") is not None
                    else None
                )

                file_size_bytes = int(size_value) if size_value else 0
                unpacked_bytes = int(unpacked_value) if unpacked_value else 0

                file_info = {
                    "file_name": file_name,
                    "package": package,
                    "size_bytes": file_size_bytes,
                    "size_formatted": format_size(size_value) if size_value else "0 B",
                    "unpacked_bytes": unpacked_bytes,
                    "unpacked_formatted": format_size(unpacked_value)
                    if unpacked_value
                    else "0 B",
                }

                patch_info["files"].append(file_info)

                # Update totals
                total_file_count += 1
                total_compressed_size += file_size_bytes
                total_uncompressed_size += unpacked_bytes

            result["patches"].append(patch_info)

    # Update build_info with calculated totals
    result["build_info"]["compressed_size"] = format_size_gb(total_compressed_size)
    result["build_info"]["uncompressed_size"] = format_size_gb(total_uncompressed_size)
    result["build_info"]["file_count"] = total_file_count

    # Check for delay preload
    delay_preload_element = root.find("delay_preload")
    if (
        delay_preload_element is not None
        and delay_preload_element.text is not None
        and delay_preload_element.text.strip().lower() == "true"
    ):
        result["delay_preload"] = True

    return result


# Save JSON data
def save_json_data(data):
    # Load existing data if it exists
    if os.path.exists(OUTPUT_JSON_FILE):
        with open(OUTPUT_JSON_FILE, "r", encoding="utf-8") as file:
            all_data = json.load(file)
    else:
        all_data = {"last_updated": datetime.now().isoformat(), "builds": {}}

    # Add or update this build
    build_name = data["build_info"]["display_name"]
    content_hash = data["build_info"]["content_hash"]

    if build_name not in all_data["builds"]:
        all_data["builds"][build_name] = {}

    # Store build data by hash for easy lookup
    all_data["builds"][build_name][content_hash] = data

    # Update timestamp
    all_data["last_updated"] = datetime.now().isoformat()

    # Save pretty JSON
    with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as file:
        json.dump(all_data, file, indent=2, ensure_ascii=False)

    print(f"Saved build data to {OUTPUT_JSON_FILE}")
    return all_data


async def check_changes():
    # Collect all HEAT build URLs
    build_urls = []
    for game_id, game_info in game_codes.items():
        cdnUrl = game_info["cdn"]
        display_name = game_info["display_name"]
        final_url, build_date = await get_metadata(game_id, cdnUrl)
        if final_url:
            build_urls.append(
                (final_url, game_info.get("secret"), display_name, build_date)
            )

    async with aiohttp.ClientSession() as session:
        for url, secret, display_name, build_date in build_urls:
            if url is None:
                continue
            filename = extract_filename_from_url(url, display_name)
            print(f"Checking: {filename}")

            content = await fetch_content(session, url)
            if content is None:
                continue

            # Parse version name
            root = ET.fromstring(content)
            version_name_elem = root.find("version_name")
            version_name = (
                version_name_elem.text.strip()
                if version_name_elem is not None and version_name_elem.text
                else ""
            )

            # Create hash for the content
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

            # Process and save as JSON
            json_data = process_xml_to_json(
                content, display_name, build_date, version_name, content_hash
            )
            if json_data:
                # Apply secret to web seed URLs if needed
                if secret:
                    for seed in json_data["web_seeds"]:
                        if "{secret}" in seed["url"]:
                            seed["url"] = seed["url"].replace("{secret}", secret)

                # Save to pretty JSON file
                save_json_data(json_data)

                print(
                    f"Processed {len(json_data['patches'])} patches with {json_data['build_info']['file_count']} total files"
                )
                print(f"Compressed size: {json_data['build_info']['compressed_size']}")
                print(
                    f"Uncompressed size: {json_data['build_info']['uncompressed_size']}"
                )
                print(f"Build hash: {content_hash}")


async def main():
    print("World of Tanks: HEAT Build Monitor")

    print(f"Starting check...")
    await check_changes()
    print(f"Check completed.")


if __name__ == "__main__":
    asyncio.run(main())
