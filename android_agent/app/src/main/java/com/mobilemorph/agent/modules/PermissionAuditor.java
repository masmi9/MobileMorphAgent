package com.mobilemorph.agent.modules;

import android.content.Context;
import android.content.pm.*;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * PermissionAuditor - Audits permissions across applications
 *
 * Features:
 * - List all permissions requested by an app
 * - Identify dangerous permissions
 * - Check permission grant status
 * - Find apps with specific permissions
 *
 * Similar to: drozer run app.package.permission
 */
public class PermissionAuditor {
    private static final String TAG = "PermissionAuditor";
    private Context context;

    // Dangerous permissions (subset - expand as needed)
    private static final String[] DANGEROUS_PERMISSIONS = {
        "android.permission.READ_CONTACTS",
        "android.permission.WRITE_CONTACTS",
        "android.permission.READ_SMS",
        "android.permission.SEND_SMS",
        "android.permission.CAMERA",
        "android.permission.RECORD_AUDIO",
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.READ_CALL_LOG",
        "android.permission.WRITE_CALL_LOG",
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.READ_CALENDAR",
        "android.permission.WRITE_CALENDAR",
        "android.permission.ACCESS_BACKGROUND_LOCATION"
    };

    public PermissionAuditor(Context context) {
        this.context = context;
    }

    public JSONObject audit(JSONObject args) {
        try {
            String packageName = args.optString("package", null);
            String findPermission = args.optString("find_permission", null);

            if (packageName != null) {
                // Audit specific package
                return auditPackage(packageName);
            } else if (findPermission != null) {
                // Find all packages with specific permission
                return findPackagesWithPermission(findPermission);
            } else {
                // List all dangerous permissions across all apps
                return auditAllDangerousPermissions();
            }

        } catch (Exception e) {
            Log.e(TAG, "Error auditing permissions", e);
            return createResponse("error", null, "Audit failed: " + e.getMessage());
        }
    }

    private JSONObject auditPackage(String packageName) throws Exception {
        PackageManager pm = context.getPackageManager();
        PackageInfo pkgInfo = pm.getPackageInfo(packageName, PackageManager.GET_PERMISSIONS);

        JSONObject result = new JSONObject();
        result.put("package", packageName);

        JSONArray permissions = new JSONArray();
        JSONArray dangerousPerms = new JSONArray();

        if (pkgInfo.requestedPermissions != null) {
            for (int i = 0; i < pkgInfo.requestedPermissions.length; i++) {
                String perm = pkgInfo.requestedPermissions[i];

                JSONObject permObj = new JSONObject();
                permObj.put("permission", perm);
                permObj.put("granted", (pkgInfo.requestedPermissionsFlags[i] & PackageInfo.REQUESTED_PERMISSION_GRANTED) != 0);

                // Check if dangerous
                boolean isDangerous = false;
                for (String dangerousPerm : DANGEROUS_PERMISSIONS) {
                    if (perm.equals(dangerousPerm)) {
                        isDangerous = true;
                        dangerousPerms.put(permObj);
                        break;
                    }
                }
                permObj.put("dangerous", isDangerous);

                permissions.put(permObj);
            }
        }

        result.put("total_permissions", permissions.length());
        result.put("dangerous_permissions_count", dangerousPerms.length());
        result.put("permissions", permissions);
        result.put("dangerous_permissions", dangerousPerms);

        return createResponse("success", result, null);
    }

    private JSONObject findPackagesWithPermission(String targetPermission) throws Exception {
        PackageManager pm = context.getPackageManager();
        JSONArray matches = new JSONArray();

        for (PackageInfo pkg : pm.getInstalledPackages(PackageManager.GET_PERMISSIONS)) {
            if (pkg.requestedPermissions != null) {
                for (String perm : pkg.requestedPermissions) {
                    if (perm.equals(targetPermission)) {
                        JSONObject match = new JSONObject();
                        match.put("package", pkg.packageName);
                        match.put("version", pkg.versionName);
                        matches.put(match);
                        break;
                    }
                }
            }
        }

        JSONObject result = new JSONObject();
        result.put("permission", targetPermission);
        result.put("found_count", matches.length());
        result.put("packages", matches);

        return createResponse("success", result, null);
    }

    private JSONObject auditAllDangerousPermissions() throws Exception {
        PackageManager pm = context.getPackageManager();
        JSONArray findings = new JSONArray();

        for (PackageInfo pkg : pm.getInstalledPackages(PackageManager.GET_PERMISSIONS)) {
            if (pkg.requestedPermissions != null) {
                JSONArray dangerousPerms = new JSONArray();

                for (int i = 0; i < pkg.requestedPermissions.length; i++) {
                    String perm = pkg.requestedPermissions[i];

                    for (String dangerousPerm : DANGEROUS_PERMISSIONS) {
                        if (perm.equals(dangerousPerm)) {
                            JSONObject permObj = new JSONObject();
                            permObj.put("permission", perm);
                            permObj.put("granted", (pkg.requestedPermissionsFlags[i] & PackageInfo.REQUESTED_PERMISSION_GRANTED) != 0);
                            dangerousPerms.put(permObj);
                            break;
                        }
                    }
                }

                if (dangerousPerms.length() > 0) {
                    JSONObject finding = new JSONObject();
                    finding.put("package", pkg.packageName);
                    finding.put("dangerous_permissions", dangerousPerms);
                    findings.put(finding);
                }
            }
        }

        JSONObject result = new JSONObject();
        result.put("total_apps_with_dangerous_perms", findings.length());
        result.put("findings", findings);

        return createResponse("success", result, null);
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
