/* The app shell's single scroll container (the ScrollArea viewport).
 * Module-scope ref so route views can attach follow-scroll behavior
 * without threading a ref through the router. */
const refAppViewport: { current: HTMLDivElement | null } = { current: null };

export { refAppViewport };
