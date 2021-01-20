
import msilib, os
dirname = os.path.dirname(__file__)
ActionText = [('InstallValidate', 'Validating install', None), ('InstallFiles', 'Copying new files', 'File: [1],  Directory: [9],  Size: [6]'), ('InstallAdminPackage', 'Copying network install files', 'File: [1], Directory: [9], Size: [6]'), ('FileCost', 'Computing space requirements', None), ('CostInitialize', 'Computing space requirements', None), ('CostFinalize', 'Computing space requirements', None), ('CreateShortcuts', 'Creating shortcuts', 'Shortcut: [1]'), ('PublishComponents', 'Publishing Qualified Components', 'Component ID: [1], Qualifier: [2]'), ('PublishFeatures', 'Publishing Product Features', 'Feature: [1]'), ('PublishProduct', 'Publishing product information', None), ('RegisterClassInfo', 'Registering Class servers', 'Class Id: [1]'), ('RegisterExtensionInfo', 'Registering extension servers', 'Extension: [1]'), ('RegisterMIMEInfo', 'Registering MIME info', 'MIME Content Type: [1], Extension: [2]'), ('RegisterProgIdInfo', 'Registering program identifiers', 'ProgId: [1]'), ('AllocateRegistrySpace', 'Allocating registry space', 'Free space: [1]'), ('AppSearch', 'Searching for installed applications', 'Property: [1], Signature: [2]'), ('BindImage', 'Binding executables', 'File: [1]'), ('CCPSearch', 'Searching for qualifying products', None), ('CreateFolders', 'Creating folders', 'Folder: [1]'), ('DeleteServices', 'Deleting services', 'Service: [1]'), ('DuplicateFiles', 'Creating duplicate files', 'File: [1],  Directory: [9],  Size: [6]'), ('FindRelatedProducts', 'Searching for related applications', 'Found application: [1]'), ('InstallODBC', 'Installing ODBC components', None), ('InstallServices', 'Installing new services', 'Service: [2]'), ('LaunchConditions', 'Evaluating launch conditions', None), ('MigrateFeatureStates', 'Migrating feature states from related applications', 'Application: [1]'), ('MoveFiles', 'Moving files', 'File: [1],  Directory: [9],  Size: [6]'), ('PatchFiles', 'Patching files', 'File: [1],  Directory: [2],  Size: [3]'), ('ProcessComponents', 'Updating component registration', None), ('RegisterComPlus', 'Registering COM+ Applications and Components', 'AppId: [1]{{, AppType: [2], Users: [3], RSN: [4]}}'), ('RegisterFonts', 'Registering fonts', 'Font: [1]'), ('RegisterProduct', 'Registering product', '[1]'), ('RegisterTypeLibraries', 'Registering type libraries', 'LibID: [1]'), ('RegisterUser', 'Registering user', '[1]'), ('RemoveDuplicateFiles', 'Removing duplicated files', 'File: [1], Directory: [9]'), ('RemoveEnvironmentStrings', 'Updating environment strings', 'Name: [1], Value: [2], Action [3]'), ('RemoveExistingProducts', 'Removing applications', 'Application: [1], Command line: [2]'), ('RemoveFiles', 'Removing files', 'File: [1], Directory: [9]'), ('RemoveFolders', 'Removing folders', 'Folder: [1]'), ('RemoveIniValues', 'Removing INI files entries', 'File: [1],  Section: [2],  Key: [3], Value: [4]'), ('RemoveODBC', 'Removing ODBC components', None), ('RemoveRegistryValues', 'Removing system registry values', 'Key: [1], Name: [2]'), ('RemoveShortcuts', 'Removing shortcuts', 'Shortcut: [1]'), ('RMCCPSearch', 'Searching for qualifying products', None), ('SelfRegModules', 'Registering modules', 'File: [1], Folder: [2]'), ('SelfUnregModules', 'Unregistering modules', 'File: [1], Folder: [2]'), ('SetODBCFolders', 'Initializing ODBC directories', None), ('StartServices', 'Starting services', 'Service: [1]'), ('StopServices', 'Stopping services', 'Service: [1]'), ('UnpublishComponents', 'Unpublishing Qualified Components', 'Component ID: [1], Qualifier: [2]'), ('UnpublishFeatures', 'Unpublishing Product Features', 'Feature: [1]'), ('UnregisterClassInfo', 'Unregister Class servers', 'Class Id: [1]'), ('UnregisterComPlus', 'Unregistering COM+ Applications and Components', 'AppId: [1]{{, AppType: [2]}}'), ('UnregisterExtensionInfo', 'Unregistering extension servers', 'Extension: [1]'), ('UnregisterFonts', 'Unregistering fonts', 'Font: [1]'), ('UnregisterMIMEInfo', 'Unregistering MIME info', 'MIME Content Type: [1], Extension: [2]'), ('UnregisterProgIdInfo', 'Unregistering program identifiers', 'ProgId: [1]'), ('UnregisterTypeLibraries', 'Unregistering type libraries', 'LibID: [1]'), ('WriteEnvironmentStrings', 'Updating environment strings', 'Name: [1], Value: [2], Action [3]'), ('WriteIniValues', 'Writing INI files values', 'File: [1],  Section: [2],  Key: [3], Value: [4]'), ('WriteRegistryValues', 'Writing system registry values', 'Key: [1], Name: [2], Value: [3]'), ('Advertise', 'Advertising application', None), ('GenerateScript', 'Generating script operations for action:', '[1]'), ('InstallSFPCatalogFile', 'Installing system catalog', 'File: [1],  Dependencies: [2]'), ('MsiPublishAssemblies', 'Publishing assembly information', 'Application Context:[1], Assembly Name:[2]'), ('MsiUnpublishAssemblies', 'Unpublishing assembly information', 'Application Context:[1], Assembly Name:[2]'), ('Rollback', 'Rolling back action:', '[1]'), ('RollbackCleanup', 'Removing backup files', 'File: [1]'), ('UnmoveFiles', 'Removing moved files', 'File: [1], Directory: [9]'), ('UnpublishProduct', 'Unpublishing product information', None)]
UIText = [('AbsentPath', None), ('bytes', 'bytes'), ('GB', 'GB'), ('KB', 'KB'), ('MB', 'MB'), ('MenuAbsent', 'Entire feature will be unavailable'), ('MenuAdvertise', 'Feature will be installed when required'), ('MenuAllCD', 'Entire feature will be installed to run from CD'), ('MenuAllLocal', 'Entire feature will be installed on local hard drive'), ('MenuAllNetwork', 'Entire feature will be installed to run from network'), ('MenuCD', 'Will be installed to run from CD'), ('MenuLocal', 'Will be installed on local hard drive'), ('MenuNetwork', 'Will be installed to run from network'), ('ScriptInProgress', 'Gathering required information...'), ('SelAbsentAbsent', 'This feature will remain uninstalled'), ('SelAbsentAdvertise', 'This feature will be set to be installed when required'), ('SelAbsentCD', 'This feature will be installed to run from CD'), ('SelAbsentLocal', 'This feature will be installed on the local hard drive'), ('SelAbsentNetwork', 'This feature will be installed to run from the network'), ('SelAdvertiseAbsent', 'This feature will become unavailable'), ('SelAdvertiseAdvertise', 'Will be installed when required'), ('SelAdvertiseCD', 'This feature will be available to run from CD'), ('SelAdvertiseLocal', 'This feature will be installed on your local hard drive'), ('SelAdvertiseNetwork', 'This feature will be available to run from the network'), ('SelCDAbsent', "This feature will be uninstalled completely, you won't be able to run it from CD"), ('SelCDAdvertise', 'This feature will change from run from CD state to set to be installed when required'), ('SelCDCD', 'This feature will remain to be run from CD'), ('SelCDLocal', 'This feature will change from run from CD state to be installed on the local hard drive'), ('SelChildCostNeg', 'This feature frees up [1] on your hard drive.'), ('SelChildCostPos', 'This feature requires [1] on your hard drive.'), ('SelCostPending', 'Compiling cost for this feature...'), ('SelLocalAbsent', 'This feature will be completely removed'), ('SelLocalAdvertise', 'This feature will be removed from your local hard drive, but will be set to be installed when required'), ('SelLocalCD', 'This feature will be removed from your local hard drive, but will be still available to run from CD'), ('SelLocalLocal', 'This feature will remain on you local hard drive'), ('SelLocalNetwork', 'This feature will be removed from your local hard drive, but will be still available to run from the network'), ('SelNetworkAbsent', "This feature will be uninstalled completely, you won't be able to run it from the network"), ('SelNetworkAdvertise', 'This feature will change from run from network state to set to be installed when required'), ('SelNetworkLocal', 'This feature will change from run from network state to be installed on the local hard drive'), ('SelNetworkNetwork', 'This feature will remain to be run from the network'), ('SelParentCostNegNeg', 'This feature frees up [1] on your hard drive. It has [2] of [3] subfeatures selected. The subfeatures free up [4] on your hard drive.'), ('SelParentCostNegPos', 'This feature frees up [1] on your hard drive. It has [2] of [3] subfeatures selected. The subfeatures require [4] on your hard drive.'), ('SelParentCostPosNeg', 'This feature requires [1] on your hard drive. It has [2] of [3] subfeatures selected. The subfeatures free up [4] on your hard drive.'), ('SelParentCostPosPos', 'This feature requires [1] on your hard drive. It has [2] of [3] subfeatures selected. The subfeatures require [4] on your hard drive.'), ('TimeRemaining', 'Time remaining: {[1] minutes }{[2] seconds}'), ('VolumeCostAvailable', 'Available'), ('VolumeCostDifference', 'Difference'), ('VolumeCostRequired', 'Required'), ('VolumeCostSize', 'Disk Size'), ('VolumeCostVolume', 'Volume')]
tables = ['ActionText', 'UIText']
