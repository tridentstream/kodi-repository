#!/usr/bin/env python

import argparse
import hashlib
import logging
import os
import subprocess
import zipfile
from io import BytesIO
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

WEBSITE_BRANCH = "website"
DEFAULT_BRANCH = "master"


def parse_addon_xml(path):
    tree = ElementTree.parse(path)
    addon = tree.getroot()

    return addon.attrib["id"], addon.attrib["version"]


def create_zip(path, addon_id):
    bio = BytesIO()
    z = zipfile.ZipFile(bio, "w")

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d[0] == "."]
        files[:] = [
            f for f in files if os.path.splitext(f)[1] not in [".pyd", ".pyo", ".pyc"]
        ]
        for file in files:
            z.write(
                os.path.join(root, file),
                os.path.join(addon_id, root[len(path) :].strip(os.sep), file),
            )
    z.close()

    bio.seek(0)
    return bio


def build_package(path, target_path):
    addon_xml_path = os.path.join(path, "addon.xml")
    if not os.path.isfile(addon_xml_path):
        logger.warning("no addon xml found %s in %s" % (branch, path,))
        raise Exception()

    addon_id, version = parse_addon_xml(addon_xml_path)
    with open(addon_xml_path, "rb") as f:
        xml_bio = BytesIO(f.read())
        xml_bio.seek(0)

    target_path = os.path.join(target_path, addon_id)
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    filename = os.path.join(target_path, "%s-%s.zip" % (addon_id, version))
    xml_filename = os.path.join(target_path, "%s-%s.xml" % (addon_id, version))

    bio = create_zip(path, addon_id)
    subprocess.check_call(["git", "checkout", WEBSITE_BRANCH])
    with open(filename, "wb") as f:
        f.write(bio.read())

    with open(xml_filename, "wb") as f:
        f.write(xml_bio.read())

    try:
        subprocess.check_call(["git", "add", filename, xml_filename])
        subprocess.check_call(
            [
                "git",
                "commit",
                "-m",
                "Updated package %s with version %s" % (addon_id, version),
            ]
        )
    finally:
        subprocess.check_call(["git", "checkout", DEFAULT_BRANCH])


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description="Package addon for Kodi")
    parser.add_argument("package_path")
    parser.add_argument("target_path")

    args = parser.parse_args()

    build_package(args.package_path, args.target_path)
