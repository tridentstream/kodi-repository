#!/usr/bin/env python3

import glob
import hashlib
import os
import subprocess
from datetime import datetime
from urllib.parse import quote
from xml.etree import ElementTree

import jinja2

WEBSITE_BRANCH = "website"
DEFAULT_BRANCH = "master"
REPOSITORIES = [
    "nightly",
    "stable",
]


def intify(v):
    v = v.split(".")
    r = []
    for vv in v:
        try:
            r.append(int(vv))
        except ValueError:
            r.append(vv)

    return tuple(r)


def parse_addon_xml(repository, path):
    tree = ElementTree.parse(path)
    addon_data = tree.getroot()

    attrib = addon_data.attrib
    metadata = addon_data.find("extension[@point='xbmc.addon.metadata']")

    return (
        {
            "id": attrib["id"],
            "name": attrib["name"],
            "summary": metadata.find("summary").text,
            "description": metadata.find("description").text,
            "version": attrib["version"],
            "downloads": {
                repository: {
                    "href": quote(
                        "/%(repository)s/%(id)s/%(id)s-%(version)s.zip"
                        % {
                            "repository": repository,
                            "id": attrib["id"],
                            "version": attrib["version"],
                        }
                    ),
                    "version": attrib["version"],
                },
            },
        },
        addon_data,
    )


if __name__ == "__main__":
    with open("index.html.tmpl", "r") as f:
        template = jinja2.Template(f.read())

    repositories = {}
    items = {}
    subprocess.check_call(["git", "checkout", WEBSITE_BRANCH])
    for repository in REPOSITORIES:
        if not os.path.exists(repository):
            continue

        print('Handling repository %s' % (repository, ))
        root = ElementTree.Element("addons")

        for addon in os.listdir(repository):
            best_addon_data, best_addon_version, best_item = None, None, None

            for xml_file in glob.glob(os.path.join(repository, addon, "*.xml")):
                item, addon_data = parse_addon_xml(repository, xml_file)
                addon_version = item["version"]
                print('Found version %s of %s' % (addon_version, addon))
                if best_addon_version is None or intify(best_addon_version) < intify(
                    addon_version
                ):
                    print('Changing version for %s from %s to %s' % (addon, best_addon_version, addon_version))
                    best_addon_version = addon_version
                    best_addon_data = addon_data
                    best_item = item

            if best_addon_data:
                root.append(best_addon_data)
                addon_id = item["id"]

                if addon_id.startswith("repository."):
                    repositories[repository] = item["downloads"][repository]["href"]
                else:
                    if addon_id in items:
                        items[addon_id]["downloads"].update(best_item["downloads"])
                    else:
                        items[addon_id] = best_item

        fn = os.path.join(repository, "addons.xml")
        ElementTree.ElementTree(root).write(fn, encoding="utf-8", xml_declaration=True)

        with open(fn, "rb") as f:
            addons_hash = hashlib.md5(f.read()).hexdigest()

        fn += ".md5"
        with open(fn, "w") as f:
            f.write(addons_hash)

    with open("index.html", "w") as f:
        f.write(
            template.render(
                items=items.values(),
                repositories=repositories,
                current_datetime=datetime.now().isoformat(),
            )
        )

    try:
        subprocess.check_call(["git", "add", "."])
        subprocess.check_call(["git", "commit", "-m", "Updated index"])
    finally:
        subprocess.check_call(["git", "checkout", DEFAULT_BRANCH])
