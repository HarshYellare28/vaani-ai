// WavRecorder — captures mic audio and encodes 16 kHz mono 16-bit PCM WAV
// entirely in the browser. That's exactly the format Azure PA and Sarvam want,
// so no server-side conversion (ffmpeg) is needed.
//
// Uses an AudioWorkletNode (modern replacement for ScriptProcessorNode):
// capture runs on the audio thread, frames are posted to the main thread.

class WavRecorder {
  // onFrame, if given, receives each Float32Array of mic samples as it arrives.
  // The worklet already copies every frame across to the main thread for the
  // recording itself, so a live visualiser can read the same frames instead of
  // attaching a second AnalyserNode to the stream.
  constructor(targetSampleRate = 16000, onFrame = null) {
    this.targetSampleRate = targetSampleRate;
    this.onFrame = onFrame;
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const AC = window.AudioContext || window.webkitAudioContext;
    this.ctx = new AC();
    // AudioContext can start suspended; without resuming, no audio is captured.
    if (this.ctx.state === "suspended") await this.ctx.resume();

    await this.ctx.audioWorklet.addModule("recorder-worklet.js");

    this.source = this.ctx.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.ctx, "capture-processor");
    // A muted gain node keeps the graph pulling without echoing the mic back.
    this.mute = this.ctx.createGain();
    this.mute.gain.value = 0;

    this.buffers = [];
    this.sampleCount = 0;
    this.node.port.onmessage = (e) => {
      const ch = e.data; // already a Float32Array copy from the worklet
      this.buffers.push(ch);
      this.sampleCount += ch.length;
      if (this.onFrame) this.onFrame(ch);
    };

    this.source.connect(this.node);
    this.node.connect(this.mute);
    this.mute.connect(this.ctx.destination);
  }

  async stop() {
    this.node.port.onmessage = null;
    this.source.disconnect();
    this.node.disconnect();
    this.mute.disconnect();
    this.stream.getTracks().forEach((t) => t.stop());
    const inRate = this.ctx.sampleRate;
    const merged = this._merge(this.buffers);
    const down = this._downsample(merged, inRate, this.targetSampleRate);
    const wav = this._encodeWav(down, this.targetSampleRate);
    await this.ctx.close();
    const blob = new Blob([wav], { type: "audio/wav" });
    // seconds of audio actually captured — used to warn on empty recordings
    blob.capturedSeconds = inRate ? this.sampleCount / inRate : 0;
    return blob;
  }

  _merge(buffers) {
    const len = buffers.reduce((a, b) => a + b.length, 0);
    const out = new Float32Array(len);
    let off = 0;
    for (const b of buffers) { out.set(b, off); off += b.length; }
    return out;
  }

  _downsample(buffer, inRate, outRate) {
    if (outRate >= inRate) return buffer;
    const ratio = inRate / outRate;
    const newLen = Math.round(buffer.length / ratio);
    const out = new Float32Array(newLen);
    for (let i = 0; i < newLen; i++) {
      const start = Math.round(i * ratio);
      const end = Math.round((i + 1) * ratio);
      let sum = 0, count = 0;
      for (let j = start; j < end && j < buffer.length; j++) { sum += buffer[j]; count++; }
      out[i] = count ? sum / count : 0;
    }
    return out;
  }

  _encodeWav(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    const writeStr = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };
    writeStr(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeStr(8, "WAVE");
    writeStr(12, "fmt ");
    view.setUint32(16, 16, true);     // PCM chunk size
    view.setUint16(20, 1, true);      // format = PCM
    view.setUint16(22, 1, true);      // channels = mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true); // byte rate
    view.setUint16(32, 2, true);      // block align
    view.setUint16(34, 16, true);     // bits per sample
    writeStr(36, "data");
    view.setUint32(40, samples.length * 2, true);
    let off = 44;
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      off += 2;
    }
    return view;
  }
}
