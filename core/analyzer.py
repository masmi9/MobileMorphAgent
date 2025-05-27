import os
import xml.etree.ElementTree as ET

class APKAnalyzer:
    def __init__(self, manifest_dir: str, decompiled_dir: str):
        self.manifest_file = os.path.join(manifest_dir, "AndroidManifest.xml")
        self.decompiled_dir = decompiled_dir

    def get_permissions(self):
        try:
            tree = ET.parse(self.manifest_file)
            root = tree.getroot()
            permissions = [
                elem.attrib['{http//schemas.android.com/apk/res/android}name'] 
                for elem in root.findall("uses-permission")
            ]
            return permissions
        except Exception as e:
            return [f"Error reading permission: {str(e)}"]
        
    def get_certificate_details(self):
        # You could integrate actual `apksigner` or `keytool` logic here later
        return "[Mocked Certificate Details]"
    
    def get_native_librarier(self):
        try:
            libs = []
            lib_dir = os.path.join(self.decompiled_dir, "lib")
            for root, _, files in os.walk(lib_dir):
                for file in files:
                    if file.endswith(".so"):
                        libs.append(os.path.join(root, file))
            return libs
        except Exception as e:
            return [f"Error: {str(e)}"]
    
    def is_debuggable(self):
        try:
            tree = ET.parse(self.manifest_file)
            root = tree.getroot()
            application = root.find("application")
            if application is not None:
                return application.get("{http://schemas.android.com/apk/res/android}debuggable") == "true"
        except Exception:
            return False
        return False