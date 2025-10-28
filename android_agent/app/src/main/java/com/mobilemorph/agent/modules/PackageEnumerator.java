package com.mobilemorph.agent.modules;

import android.content.Context;
import android.content.pm.*;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.List;

/**
 * PackageEnumerator - Enumerates all installed packages
 *
 * Features:
 * - List all installed applications
 * - Filter by system/user apps
 * - Show exported components per package
 * - Identify attack surface
 *
 * Similar to: drozer run app.package.list
 */
public class PackageEnumerator {
    private static final String TAG = "PackageEnumerator";
    private Context context;

    public PackageEnumerator(Context context) {
        this.context = context;
    }

    public JSONObject enumerate(JSONObject args) {
        try {
            boolean includeSystem = args.optBoolean("include_system", false);
            boolean exportedOnly = args.optBoolean("exported_only", false);
            String filterPackage = args.optString("filter", null);

            Log.i(TAG, "Enumerating packages (system=" + includeSystem + ", exported=" + exportedOnly + ")");

            PackageManager pm = context.getPackageManager();
            List<PackageInfo> packages = pm.getInstalledPackages(
                PackageManager.GET_ACTIVITIES |
                PackageManager.GET_SERVICES |
                PackageManager.GET_RECEIVERS |
                PackageManager.GET_PROVIDERS
            );

            JSONArray results = new JSONArray();

            for (PackageInfo pkg : packages) {
                // Filter system apps if requested
                if (!includeSystem && (pkg.applicationInfo.flags & ApplicationInfo.FLAG_SYSTEM) != 0) {
                    continue;
                }

                // Filter by package name if specified
                if (filterPackage != null && !pkg.packageName.contains(filterPackage)) {
                    continue;
                }

                JSONObject pkgObj = new JSONObject();
                pkgObj.put("package", pkg.packageName);
                pkgObj.put("version", pkg.versionName);
                pkgObj.put("is_system", (pkg.applicationInfo.flags & ApplicationInfo.FLAG_SYSTEM) != 0);

                // Count exported components
                int exportedCount = 0;
                JSONArray exportedComponents = new JSONArray();

                if (pkg.activities != null) {
                    for (ActivityInfo ai : pkg.activities) {
                        if (ai.exported) {
                            exportedCount++;
                            if (!exportedOnly || exportedOnly) {
                                JSONObject comp = new JSONObject();
                                comp.put("type", "activity");
                                comp.put("name", ai.name);
                                comp.put("permission", ai.permission);
                                exportedComponents.put(comp);
                            }
                        }
                    }
                }

                if (pkg.services != null) {
                    for (ServiceInfo si : pkg.services) {
                        if (si.exported) {
                            exportedCount++;
                            if (!exportedOnly || exportedOnly) {
                                JSONObject comp = new JSONObject();
                                comp.put("type", "service");
                                comp.put("name", si.name);
                                comp.put("permission", si.permission);
                                exportedComponents.put(comp);
                            }
                        }
                    }
                }

                if (pkg.receivers != null) {
                    for (ActivityInfo ri : pkg.receivers) {
                        if (ri.exported) {
                            exportedCount++;
                            if (!exportedOnly || exportedOnly) {
                                JSONObject comp = new JSONObject();
                                comp.put("type", "receiver");
                                comp.put("name", ri.name);
                                comp.put("permission", ri.permission);
                                exportedComponents.put(comp);
                            }
                        }
                    }
                }

                if (pkg.providers != null) {
                    for (ProviderInfo pi : pkg.providers) {
                        if (pi.exported) {
                            exportedCount++;
                            if (!exportedOnly || exportedOnly) {
                                JSONObject comp = new JSONObject();
                                comp.put("type", "provider");
                                comp.put("name", pi.name);
                                comp.put("authority", pi.authority);
                                comp.put("read_permission", pi.readPermission);
                                comp.put("write_permission", pi.writePermission);
                                exportedComponents.put(comp);
                            }
                        }
                    }
                }

                pkgObj.put("exported_count", exportedCount);
                pkgObj.put("exported_components", exportedComponents);

                // Only include if we have exported components when exportedOnly is true
                if (!exportedOnly || exportedCount > 0) {
                    results.put(pkgObj);
                }
            }

            JSONObject result = new JSONObject();
            result.put("total_packages", results.length());
            result.put("packages", results);

            return createResponse("success", result, null);

        } catch (Exception e) {
            Log.e(TAG, "Error enumerating packages", e);
            return createResponse("error", null, "Enumeration failed: " + e.getMessage());
        }
    }

    private JSONObject createResponse(String status, Object data, String error) {
        try {
            JSONObject response = new JSONObject();
            response.put("status", status);
            response.put("data", data);
            response.put("error", error);
            return response;
        } catch (Exception e) {
            return new JSONObject();
        }
    }
}
