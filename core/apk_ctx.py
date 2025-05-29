from pathlib import Path

class APKContext:
    def __init__(self, apk_path_str: str, package_name: str):
        self.apk_path = Path(apk_path_str)
        self.package_name = package_name
        #self.device_id = device_id
        self.decompiled_apk_dir = Path("decompiled") / package_name
        self.manifest_path = self.decompiled_apk_dir / "AndroidManifest.xml"
        self.scan_mode = "safe"
        self.analyzer = None
        self.drozer = None

    def set_scan_mode(self, mode: str):
        self.scan_mode = mode

    def set_apk_analyzer(self, analyzer):
        self.analyzer = analyzer
    
    def set_drozer_helper(self, drozer_helper):
        self.drozer = drozer_helper
