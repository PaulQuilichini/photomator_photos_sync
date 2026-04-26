from __future__ import annotations

import threading
from pathlib import Path

import objc

from core.models import Candidate
from core.scan_logic import VIDEO_EXTENSIONS, normalize_nsdate

objc.loadBundle("Photos", globals(), bundle_path="/System/Library/Frameworks/Photos.framework")
objc.registerMetaDataForSelector(
    b"PHPhotoLibrary",
    b"requestAuthorization:",
    {
        "arguments": {
            2: {
                "callable": {
                    "retval": {"type": b"v"},
                    "arguments": {
                        0: {"type": b"^v"},
                        1: {"type": objc._C_NSInteger},
                    },
                }
            }
        }
    },
)
objc.registerMetaDataForSelector(
    b"PHPhotoLibrary",
    b"requestAuthorizationForAccessLevel:handler:",
    {
        "arguments": {
            3: {
                "callable": {
                    "retval": {"type": b"v"},
                    "arguments": {
                        0: {"type": b"^v"},
                        1: {"type": objc._C_NSInteger},
                    },
                }
            }
        }
    },
)
objc.registerMetaDataForSelector(
    b"PHPhotoLibrary",
    b"performChangesAndWait:error:",
    {
        "arguments": {
            2: {
                "callable": {
                    "retval": {"type": b"v"},
                    "arguments": {
                        0: {"type": b"^v"},
                    },
                }
            },
            3: {
                "type_modifier": objc._C_OUT,
                "null_accepted": True,
            },
        }
    },
)

PH_AUTH_NOT_DETERMINED = 0
PH_AUTH_RESTRICTED = 1
PH_AUTH_DENIED = 2
PH_AUTH_AUTHORIZED = 3
PH_AUTH_LIMITED = 4
PH_ACCESS_READ_WRITE = 2
PH_ASSET_COLLECTION_TYPE_ALBUM = 1
PH_ASSET_COLLECTION_SUBTYPE_ALBUM_REGULAR = 2


class PhotosLibraryBridge:
    def __init__(self) -> None:
        self._authorization_cache: int | None = None
        self._asset_fingerprints: set[str] | None = None
        self._asset_names: set[str] | None = None

    def ensure_authorized(self) -> tuple[bool, str]:
        if self._authorization_cache is None:
            status = int(PHPhotoLibrary.authorizationStatusForAccessLevel_(PH_ACCESS_READ_WRITE))
            if status == PH_AUTH_NOT_DETERMINED:
                event = threading.Event()
                result = {"status": status}

                def handler(current_status: int) -> None:
                    result["status"] = int(current_status)
                    event.set()

                handler.__block_signature__ = b"vq"
                PHPhotoLibrary.requestAuthorizationForAccessLevel_handler_(PH_ACCESS_READ_WRITE, handler)
                event.wait()
                status = int(result["status"])

            self._authorization_cache = status

        status = self._authorization_cache
        if status == PH_AUTH_AUTHORIZED or status == PH_AUTH_LIMITED:
            return True, ""
        if status == PH_AUTH_DENIED:
            return False, "Photos access was denied. Allow access in System Settings > Privacy & Security > Photos."
        if status == PH_AUTH_RESTRICTED:
            return False, "Photos access is restricted by macOS and cannot be granted by this app."
        return False, "Photos access was not granted."

    def build_index(self, progress=None) -> None:
        if self._asset_fingerprints is not None and self._asset_names is not None:
            return

        assets = PHAsset.fetchAssetsWithOptions_(None)
        count = int(assets.count())
        fingerprints: set[str] = set()
        names: set[str] = set()

        for index in range(count):
            asset = assets.objectAtIndex_(index)
            resources = PHAssetResource.assetResourcesForAsset_(asset)
            if not resources:
                continue

            resource = next((item for item in resources if hasattr(item, "originalFilename")), resources[0])
            filename = str(resource.originalFilename()).lower()
            names.add(filename)
            width = int(asset.pixelWidth())
            height = int(asset.pixelHeight())
            created = normalize_nsdate(asset.creationDate())
            fingerprints.add("|".join([filename, str(width), str(height), created or "", ""]))
            if progress:
                progress(index + 1, count)

        self._asset_fingerprints = fingerprints
        self._asset_names = names

    def match_reason(self, candidate: Candidate) -> str | None:
        if self._asset_names is None or self._asset_fingerprints is None:
            raise RuntimeError("Photos index not built")

        if candidate.path.name.lower() in self._asset_names:
            return "matching filename already exists in Photos"

        loose_fingerprint = candidate.fingerprint.rsplit("|", 1)[0] + "|"
        if loose_fingerprint in self._asset_fingerprints:
            return "matching filename, size, and capture metadata already exists in Photos"

        return None

    def find_album_by_title(self, title: str):
        normalized = title.strip()
        if not normalized:
            return None
        collections = PHAssetCollection.fetchAssetCollectionsWithType_subtype_options_(
            PH_ASSET_COLLECTION_TYPE_ALBUM,
            PH_ASSET_COLLECTION_SUBTYPE_ALBUM_REGULAR,
            None,
        )
        count = int(collections.count())
        for index in range(count):
            collection = collections.objectAtIndex_(index)
            localized = str(collection.localizedTitle() or "")
            if localized == normalized:
                return collection
        return None

    def ensure_album(self, title: str):
        normalized = title.strip()
        if not normalized:
            return None, ""
        existing = self.find_album_by_title(normalized)
        if existing is not None:
            return existing, ""

        photo_library = PHPhotoLibrary.sharedPhotoLibrary()

        def change_block() -> None:
            PHAssetCollectionChangeRequest.creationRequestForAssetCollectionWithTitle_(normalized)

        ok, error = photo_library.performChangesAndWait_error_(change_block, None)
        if not ok:
            description = str(error.localizedDescription()) if error else "unknown album creation error"
            return None, description

        created = self.find_album_by_title(normalized)
        if created is None:
            return None, f"album '{normalized}' could not be found after creation"
        return created, ""

    def import_files(self, files: list[Path], album_name: str = "") -> tuple[int, list[str]]:
        errors: list[str] = []
        imported = 0
        photo_library = PHPhotoLibrary.sharedPhotoLibrary()
        target_album = None
        if album_name.strip():
            target_album, album_error = self.ensure_album(album_name)
            if album_error:
                return 0, [f"Album '{album_name}': {album_error}"]

        for path in files:
            url = NSURL.fileURLWithPath_(str(path))

            def change_block() -> None:
                if path.suffix.lower() in VIDEO_EXTENSIONS:
                    asset_request = PHAssetChangeRequest.creationRequestForAssetFromVideoAtFileURL_(url)
                else:
                    asset_request = PHAssetChangeRequest.creationRequestForAssetFromImageAtFileURL_(url)
                if target_album is not None:
                    placeholder = asset_request.placeholderForCreatedAsset()
                    album_request = PHAssetCollectionChangeRequest.changeRequestForAssetCollection_(target_album)
                    album_request.addAssets_([placeholder])

            ok, error = photo_library.performChangesAndWait_error_(change_block, None)
            if ok:
                imported += 1
                continue

            description = str(error.localizedDescription()) if error else "unknown Photos import error"
            errors.append(f"{path.name}: {description}")

        if imported:
            self._asset_fingerprints = None
            self._asset_names = None

        return imported, errors

    def delete_assets_by_identifiers(self, identifiers: list[str]) -> tuple[int, list[str]]:
        if not identifiers:
            return 0, []
        fetch_result = PHAsset.fetchAssetsWithLocalIdentifiers_options_(identifiers, None)
        count = int(fetch_result.count())
        if count == 0:
            return 0, ["No matching Photos assets were found for deletion."]

        photo_library = PHPhotoLibrary.sharedPhotoLibrary()

        def change_block() -> None:
            PHAssetChangeRequest.deleteAssets_(fetch_result)

        ok, error = photo_library.performChangesAndWait_error_(change_block, None)
        if not ok:
            description = str(error.localizedDescription()) if error else "unknown Photos delete error"
            return 0, [description]

        self._asset_fingerprints = None
        self._asset_names = None
        return count, []
