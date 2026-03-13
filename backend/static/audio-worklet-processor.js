/**
 * AudioWorklet processors for PCM capture and playback.
 * Must be a separate file per Web Audio API spec.
 */

/**
 * CaptureProcessor: captures mic audio and converts to 16-bit PCM 16kHz mono.
 * Posts PCM ArrayBuffer to the main thread via port.
 */
class CaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._bufferSize = 4096; // ~256ms at 16kHz
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const samples = input[0]; // Float32 mono channel

    // Convert Float32 to Int16 PCM
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      this._buffer.push(s < 0 ? s * 0x8000 : s * 0x7fff);
    }

    // Flush buffer when full
    if (this._buffer.length >= this._bufferSize) {
      const pcm = new Int16Array(this._buffer.splice(0, this._bufferSize));
      this.port.postMessage(pcm.buffer, [pcm.buffer]);
    }

    return true;
  }
}

/**
 * PlaybackProcessor: receives PCM 24kHz Int16 buffers and outputs Float32 audio.
 */
class PlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._queue = [];
    this._offset = 0;

    this.port.onmessage = (e) => {
      if (e.data === 'clear') {
        this._queue = [];
        this._offset = 0;
      } else if (e.data instanceof ArrayBuffer) {
        this._queue.push(new Int16Array(e.data));
      }
    };
  }

  process(inputs, outputs) {
    const output = outputs[0];
    if (!output || !output[0]) return true;

    const channel = output[0];

    for (let i = 0; i < channel.length; i++) {
      if (this._queue.length === 0) {
        channel[i] = 0;
        continue;
      }

      const currentBuffer = this._queue[0];
      channel[i] = currentBuffer[this._offset] / 32768.0;
      this._offset++;

      if (this._offset >= currentBuffer.length) {
        this._queue.shift();
        this._offset = 0;
      }
    }

    return true;
  }
}

registerProcessor('capture-processor', CaptureProcessor);
registerProcessor('playback-processor', PlaybackProcessor);
