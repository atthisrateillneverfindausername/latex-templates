#!/usr/bin/env python3
# coding=utf-8

import argparse
import datetime
import pathlib
import re
import semantic_version
import shutil


# Extension of the backup file
EXT_BACKUP = '.bak'



def make_backup(p):
    if not type(p) is pathlib.Path:
        p = pathlib.Path(p)

    # Copy file to a file with the backup file extension
    shutil.copy2(p, p.with_suffix(EXT_BACKUP))


def restore_backup(p, suffix='.cls'):
    if not type(p) is pathlib.Path:
        p = pathlib.Path(p)

    # Restore the '*.swp' file to the '*.cls' file
    shutil.copy2(p.with_suffix(EXT_BACKUP), p.with_suffix(suffix))


def remove_backup(p):
    if not type(p) is pathlib.Path:
        p = pathlib.Path(p)

    # Remove the backup file
    p.with_suffix(EXT_BACKUP).unlink()


def read_file(p):
    if not type(p) is pathlib.Path:
        p = pathlib.Path(p)

    # Open file for reading
    f = p.open('r')
    # Read all lines
    lns = f.readlines()
    # Close file again
    f.close()
    # And return the lines read
    return lns


def write_file(p, lns):
    if not type(p) is pathlib.Path:
        p = pathlib.Path(p)

    # Open file for writing
    f = p.open('w')
    # Write all lines
    retcode = f.writelines(lns)
    # Close file
    f.close()
    # And return success code of writing
    return retcode


def change_version(lns, type):
    # Pre-compile a regex-object to find the current version number in-file
    reg = re.compile('\\\\def\\\\fileversion{(?P<version>.*)}')

    # Loop over each line of the file
    for idx, l in enumerate(lns):
        # Match the regex in the current line
        version_found = reg.search(l)

        # If we found a match in the current line (we expect only one match per
        # file) we will replace the version number and then break the loop
        if version_found:
            # Get a semantic version object from the current file version
            sv = semantic_version.Version(version_found.group('version'), partial=True)
            # What shall we do with the version?
            if type == 'patch':
                sv = sv.next_patch()
            elif type == 'minor':
                sv = sv.next_minor()
            elif type == 'major':
                sv = sv.next_major()

            # And replace the old with the new version
            lns[idx] = l.replace(version_found.group('version'), str(sv))

            # No more processing of other lines
            break

    # Update file content
    return [lns, sv]


def update_filedate(lns):
    # Pre-compoile a regex-object to find the \filedate in the current file
    reg = re.compile('\\\\def\\\\filedate{(?P<filedate>.*)}')

    # Loop over each line of the file
    for idx, l in enumerate(lns):
        # Match the regex in the current line
        filedate_found = reg.search(l)

        # If we found a match in the current line (we expect only one match per
        # file) we will replace the filedate and then break the loop
        if filedate_found:
            lns[idx] = l.replace(filedate_found.group('filedate'), datetime.datetime.utcnow().strftime('%Y/%m/%d'))

            # Only one replacement necessary/expected => break out
            break

    # Return updated file content
    return lns


def bump_class(p, type):
    """
    Bumps the version number given a specific type (patch, minor, major)
    :param pathlib.Path p: Path to the file to updated
    :param str type: Type of version changing (patch, minor, or major)
    :return:
    """

    try:
        # Create a backup of the file
        make_backup(p)

        # Read the file
        lns = read_file(p)

        # Increase the version number and get the adjusted file content
        [lns, nv] = change_version(lns, type)

        # Update the filedate, too
        lns = update_filedate(lns)

        # Finally, write the new file
        write_file(p, lns)

        # Remove backup if everything was successful
        remove_backup(p)

        return nv
    except Exception as e:
        # Restore the backup file
        restore_backup(p)


def bump_readme(p, c, nv):
    """
    Writes the new version number for the given class into the readme file
    :param pathlib.Path p: Path to the file to updated
    :param str type: Type of version changing (patch, minor, or major)
    :return:
    """

    try:
        # Create a backup of the file
        make_backup(p)

        # Read the file
        lns = read_file(p)

        # Increase the version number and get the adjusted file content
        lns = update_readmeversion(lns, c, nv)

        # Finally, write the new file
        write_file(p, lns)

        # Remove backup if everything was successful
        remove_backup(p)
    except Exception as e:
        # Restore the backup file
        restore_backup(p, p.suffix)


def update_readmeversion(lns, c, nv):
    # Pre-compoile a regex-object to find the \filedate in the current file
    reg = re.compile('\|\s?' + c + '\s?\|\s?[\w\ ]*?\s?\|\s?(?P<oldversion>[\d\.]*)\s?\|')

    # Loop over each line of the file
    for idx, l in enumerate(lns):
        # Match the regex in the current line
        cls_version = reg.search(l)

        # If we found a match in the current line (we expect only one match per
        # file) we will replace the version number and then break the loop
        if cls_version:
            lns[idx] = l.replace(cls_version.group('oldversion'), str(nv))

            # Only one replacement necessary/expected => break out
            break

    # Return updated file content
    return lns



if __name__ == '__main__':
    """
    This is the main function that builds the given file
    :return:
    """
    parser = argparse.ArgumentParser(description='Bump version of LaTeX classes.')

    parser.add_argument('type', metavar='type', choices=['patch', 'minor', 'major'],
                        help='Type of version bumping to perform.')

    parser.add_argument('cls', metavar='class', nargs='+', type=str,
                        help='LaTeX class to perform semantic versioning on')

    parser.add_argument('--readme', '-r', type=str, action='store', default='README.md',
                        help='Flag to update file README.md or string to update given readme file')

    # Parse the arguments given
    args = parser.parse_args()

    # Find the files we need to update
    ps = [(pathlib.Path.cwd() / c).resolve() for c in args.cls]
    pr = (pathlib.Path.cwd() / args.readme).absolute()
    # Loop over each file
    for p in ps:
        nv = bump_class(p, args.type)

        # Update README, too?
        if len(args.readme):
            bump_readme(pr, p.stem, nv)
