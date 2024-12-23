# SPDX-License-Identifier: LGPL-2.1-or-later

from collections.abc import Iterable, Sequence
from mkosi.context import Context
from mkosi.distributions import centos, join_mirror
from mkosi.installer.rpm import RpmRepository, find_rpm_gpgkey
from mkosi.versioncomp import GenericVersion
from mkosi.log import die
from mkosi.installer.dnf import Dnf
from mkosi.installer.rpm import RpmRepository, find_rpm_gpgkey, setup_rpm


class Installer(centos.Installer):
    @classmethod
    def pretty_name(cls) -> str:
        return "Rocky Linux"

    @staticmethod
    def gpgurls(context: Context) -> tuple[str, ...]:
        return (
            find_rpm_gpgkey(
                context,
                f"RPM-GPG-KEY-Rocky-{context.config.release}",
                f"https://download.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-{context.config.release}",
            ),
        )

    @classmethod
    def repository_variants(cls, context: Context, repo: str) -> list[RpmRepository]:
        if context.config.mirror:
            url = f"baseurl={join_mirror(context.config.mirror, f'rocky/$releasever/{repo}/$basearch/os')}"
        else:
            url = f"mirrorlist=https://mirrors.rockylinux.org/mirrorlist?arch=$basearch&repo={repo}-$releasever"

        return [RpmRepository(repo, url, cls.gpgurls(context))]

    @classmethod
    def sig_repositories(cls, context: Context) -> list[RpmRepository]:
        return []

    @classmethod
    def setup(cls, context: Context) -> None:
        if GenericVersion(context.config.release) <= 7:
            die(f"{cls.pretty_name()} 7 or earlier variants are not supported")

        Dnf.setup(context, list(cls.repositories(context)))
        (context.sandbox_tree / "etc/dnf/vars/stream").write_text(f"{context.config.release}-stream\n")
        setup_rpm(context, dbpath=cls.dbpath(context))

    @classmethod
    def repositories(cls, context: Context) -> Iterable[RpmRepository]:
        if context.config.local_mirror:
            yield from cls.repository_variants(context, "AppStream")
            return

        yield from cls.repository_variants(context, "BaseOS")
        yield from cls.repository_variants(context, "AppStream")
        yield from cls.repository_variants(context, "extras")

        if GenericVersion(context.config.release) >= 9:
            yield from cls.repository_variants(context, "CRB")
        else:
            yield from cls.repository_variants(context, "PowerTools")

        yield from cls.epel_repositories(context)
        yield from cls.sig_repositories(context)
