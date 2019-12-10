import sys
import yaml

from intake.cli.bootstrap import main as run
from intake.cli.util import Subcommand

from .catalog import DCATCatalog
from .util import mirror_data


class Mirror(Subcommand):
    """
    Mirror a catalog subset specified in a manifest to a remote bucket,
    and print the resulting subsetted catalog to stdout.


    If --dry-run is specified, then no upload happens, but the catalog is still printed.
    """

    name = "mirror"

    def initialize(self):
        """
        Initialize the subcommand by adding the argparser arguments.
        """
        self.parser.add_argument(
            "manifest",
            type=str,
            metavar="MANIFEST",
            help="Path to a manifest YAML file",
        )
        self.parser.add_argument(
            "--dry-run",
            help="If this flag is given, no upload occurs",
            action="store_true",
        )
        self.parser.add_argument(
            "--version", metavar="VERSION", type=str, help="Catalog version"
        )
        self.parser.add_argument(
            "--name", metavar="VERSION", type=str, help="Catalog name"
        )

    def invoke(self, args):
        """
        Invoke the command.
        """
        upload = not args.dry_run
        catalog = mirror_data(
            args.manifest, upload=upload, name=args.name, version=args.version
        )
        print(yaml.dump(catalog))


class Create(Subcommand):
    """
    Create an intake YAML catalog from a DCAT catalog and print it to stdout.
    """

    name = "create"

    def initialize(self):
        """
        Initialize the subcommand by adding the argparser arguments.
        """
        self.parser.add_argument("uri", metavar="URI", type=str, help="Catalog URI")
        self.parser.add_argument(
            "--version", metavar="VERSION", type=str, help="Catalog version"
        )
        self.parser.add_argument(
            "--name", metavar="VERSION", type=str, help="Catalog name"
        )

    def invoke(self, args):
        """
        Invoke the command.
        """
        version = args.version or None
        name = args.name or ""
        metadata = {"name": name, "version": version}
        catalog = DCATCatalog(args.uri, name=name, metadata=metadata)
        print(catalog.serialize())


subcommands = [Mirror, Create]


def main(argv=None):
    return run("Intake DCAT CLI", subcommands, argv or sys.argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
