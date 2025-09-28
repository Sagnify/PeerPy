import resolve from "@rollup/plugin-node-resolve";
import commonjs from "@rollup/plugin-commonjs";

export default {
  input: "myrtclib.js", // source file
  output: [
    {
      file: "dist/peerpyrtc.esm.js",  // modern ES module
      format: "es"
    },
    {
      file: "dist/peerpyrtc.umd.js",  // UMD for CDN
      format: "umd",
      name: "WebRTCConnection"        // global name when loaded via <script>
    }
  ],
  plugins: [resolve(), commonjs()]
};
