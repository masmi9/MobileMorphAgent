package src.main.java.com.mobilemorph.agent.util;

public class NeworkUtils {
    public static void addAuthHeaders(HttpURLConnection conn, String agentId, String sharedKey) throws Exception {
        String sig = hmacSha256(agentId, sharedKey);
        conn.setRequestProperty("X-Agent-ID", agentId);
        conn.setRequestProperty("X-Signature", sig);
    }

    private static String hmacSha256(String data, String key) throws Exception {
        SecretKeySpec secretKey = new SecretKeySpec(key.getBytes("UTF-8"), "HmacSHA256");
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(secretKey);
        byte[] bytes = mac.doFinal(data.getBytes("UTF-8"));
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) sb.append(String.format("%02x", b));
        return sb.toString();
    }
}
