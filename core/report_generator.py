import json

class ReportGenerator:
    def __init__(self, package_name, scan_mode):
        self.package_name = package_name
        self.scan_mode = scan_mode
        self.sections = []
        self.meta = {}

    def add_section(self, title, content):
        self.sections.append((title, content))

    def add_metadata(self, key, value):
        self.meta[key] = value

    def generate_html(self, path):
        with open(path, "w") as f:
            f.write("<html><head><title>Security Report</title></head><body>")
            f.write(f"<h1>Security Report for {self.package_name}</h1>")
            for title, content in self.sections:
                f.write(f"<h2>{title}</h2><pre>{content}</pre>")
            f.write("</body></html>")

    def generate_json(self, path):
        with open(path, "w") as f:
            json.dump({"sections": self.sections, "meta": self.meta}, f, indent=2)

    def generate_csv(self, path):
        with open(path, "w") as f:
            for title, content in self.sections:
                f.write(f'"{title}","{content}"')

    def generate_all_formats(self):
        base = f"{self.package_name}_security_report"
        files = {
            "html": f"{base}.html",
            "json": f"{base}.json",
            "csv": f"{base}.csv"
        }
        self.generate_html(files["html"])
        self.generate_json(files["json"])
        self.generate_csv(files["csv"])
        return files