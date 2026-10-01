declare module 'butterchurn' {
  type Visualizer = {
    connectAudio(node: AudioNode): void
    disconnectAudio(node: AudioNode): void
    loadPreset(preset: unknown, seconds: number): void
    setRendererSize(width: number, height: number): void
    render(): void
  }
  type Butterchurn = {
    createVisualizer(
      context: AudioContext,
      canvas: HTMLCanvasElement,
      options: { width: number; height: number; pixelRatio?: number; textureRatio?: number },
    ): Visualizer
  }
  const module: Butterchurn | { default: Butterchurn }
  export default module
}
