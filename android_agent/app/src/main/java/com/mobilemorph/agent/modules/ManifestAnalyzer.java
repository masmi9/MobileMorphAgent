package com.mobilemorph.agent.modules;

import android.content.Context;
import android.content.pm.*;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * ManifestAnalyzer - Analyzes AndroidManifest.xml of target applications
 *
 * Features:
 * - Extract all components (activities, services, receivers, providers)
 * - Identify exported components
 * - List permissions
 * - Check security flags (debuggable, allowBackup, etc.)
 *
 * Similar to: drozer run app.package.manifest
 */
public class ManifestAnalyzer {
    private static final String TAG = "ManifestAnalyzer";
    private Context context;

    public ManifestAnalyzer(Context context) {
        this.context = context;
    }

    public JSONObject analyze(JSONObject args) {
        try {
            String packageName = args.optString("package", context.getPackageName());
            Log.i(TAG, "Analyzing manifest for: " + packageName);

            PackageManager pm = context.getPackageManager();
            PackageInfo pkgInfo = pm.getPackageInfo(packageName,
                PackageManager.GET_ACTIVITIES |
                PackageManager.GET_SERVICES |
                PackageManager.GET_RECEIVERS |
                PackageManager.GET_PROVIDERS |
                PackageManager.GET_PERMISSIONS |
                PackageManager.GET_META_DATA);

            JSONObject result = new JSONObject();
            result.put("package_name", packageName);
            result.put("version_name", pkgInfo.versionName);
            result.put("version_code", pkgInfo.versionCode);

            // Application flags
            ApplicationInfo appInfo = pkgInfo.applicationInfo;
            JSONObject flags = new JSONObject();
            flags.put("debuggable", (appInfo.flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0);
            flags.put("allow_backup", (appInfo.flags & ApplicationInfo.FLAG_ALLOW_BACKUP) != 0);
            flags.put("test_only", (appInfo.flags & ApplicationInfo.FLAG_TEST_ONLY) != 0);
            flags.put("has_code", (appInfo.flags & ApplicationInfo.FLAG_HAS_CODE) != 0);
            flags.put("target_sdk", appInfo.targetSdkVersion);
            flags.put("min_sdk", appInfo.minSdkVersion);
            flags.put("shared_user_id", appInfo.sharedUserId);
            result.put("flags", flags);

            // Activities
            JSONArray activities = new JSONArray();
            if (pkgInfo.activities != null) {
                for (ActivityInfo ai : pkgInfo.activities) {
                    JSONObject activity = new JSONObject();
                    activity.put("name", ai.name);
                    activity.put("exported", ai.exported);
                    activity.put("permission", ai.permission);
                    activity.put("task_affinity", ai.taskAffinity);
                    activities.put(activity);
                }
            }
            result.put("activities", activities);

            // Services
            JSONArray services = new JSONArray();
            if (pkgInfo.services != null) {
                for (ServiceInfo si : pkgInfo.services) {
                    JSONObject service = new JSONObject();
                    service.put("name", si.name);
                    service.put("exported", si.exported);
                    service.put("permission", si.permission);
                    services.put(service);
                }
            }
            result.put("services", services);

            // Broadcast Receivers
            JSONArray receivers = new JSONArray();
            if (pkgInfo.receivers != null) {
                for (ActivityInfo ri : pkgInfo.receivers) {
                    JSONObject receiver = new JSONObject();
                    receiver.put("name", ri.name);
                    receiver.put("exported", ri.exported);
                    receiver.put("permission", ri.permission);
                    receivers.put(receiver);
                }
            }
            result.put("receivers", receivers);

            // Content Providers
            JSONArray providers = new JSONArray();
            if (pkgInfo.providers != null) {
                for (ProviderInfo pi : pkgInfo.providers) {
                    JSONObject provider = new JSONObject();
                    provider.put("name", pi.name);
                    provider.put("authority", pi.authority);
                    provider.put("exported", pi.exported);
                    provider.put("read_permission", pi.readPermission);
                    provider.put("write_permission", pi.writePermission);
                    provider.put("grant_uri_permissions", pi.grantUriPermissions);
                    providers.put(provider);
                }
            }
            result.put("providers", providers);

            // Permissions
            JSONArray permissions = new JSONArray();
            if (pkgInfo.requestedPermissions != null) {
                for (String perm : pkgInfo.requestedPermissions) {
                    permissions.put(perm);
                }
            }
            result.put("permissions", permissions);

            return createResponse("success", result, null);

        } catch (PackageManager.NameNotFoundException e) {
            return createResponse("error", null, "Package not found: " + e.getMessage());
        } catch (Exception e) {
            Log.e(TAG, "Error analyzing manifest", e);
            return createResponse("error", null, "Analysis failed: " + e.getMessage());
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
