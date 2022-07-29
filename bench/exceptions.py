class InvalidBranchException(Exception):
	pass


class InvalidRemoteException(Exception):
	pass


class PatchError(Exception):
	pass


class CommandFailedError(Exception):
	pass


class BenchNotFoundError(Exception):
	pass


class ValidationError(Exception):
	pass


class AppNotInstalledError(ValidationError):
	pass


class CannotUpdateReleaseBench(ValidationError):
	pass


class FeatureDoesNotExistError(CommandFailedError):
	pass


class NotInBenchDirectoryError(Exception):
	pass


class VersionNotFound(Exception):
	pass
