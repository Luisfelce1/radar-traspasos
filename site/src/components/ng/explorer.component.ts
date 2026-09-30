import {
  afterNextRender, ChangeDetectionStrategy, Component, computed, DestroyRef, ElementRef, inject, input, signal, viewChild,
} from "@angular/core";
import { VoltInput, VoltNativeButton, VoltNativeSelect, VoltSkeleton } from "@voltui/components";
import { ListingCardComponent } from "./listing-card.component";
import { matches, SECTORES, shuffle, TIPOS } from "./model";
import type { Filters, Row } from "./model";

const PAGE = 24;
const PRICES = [25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000];
const EMPTY: Filters = { q: "", sector: "", provincia: "", tipo: "", max: 0 };

/**
 * Explorador de anuncios: filtros + rejilla en ORDEN ALEATORIO (distinto en cada visita)
 * con carga continua al hacer scroll.
 * - En el build (SSR) pinta `initial` para que Google vea anuncios reales.
 * - En el navegador descarga /listings-index.json, baraja y toma el control.
 */
@Component({
  selector: "app-explorer",
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ListingCardComponent, VoltInput, VoltNativeButton, VoltNativeSelect, VoltSkeleton],
  host: { class: "block" },
  template: `
    <section aria-label="Filtros" class="z-20 -mx-4 mb-6 md:sticky md:top-16 border-b border-border bg-background/85 px-4 py-3 backdrop-blur-md sm:mx-0 sm:rounded-xl sm:border sm:shadow-sm">
      <div class="grid gap-2 md:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))]">
        <volt-input
          aria-label="Buscar"
          placeholder="Busca: cafetería, peluquería, Valencia…"
          [value]="filters().q"
          (valueChange)="set('q', $event)" />
        <select voltNativeSelect aria-label="Sector" (change)="set('sector', $any($event.target).value)">
          <option value="">Todos los sectores</option>
          @for (s of sectorOptions; track s[0]) {
            <option [value]="s[0]" [selected]="filters().sector === s[0]">{{ s[1] }}</option>
          }
        </select>
        <select voltNativeSelect aria-label="Provincia" (change)="set('provincia', $any($event.target).value)">
          <option value="">Todas las provincias</option>
          @for (p of provincias(); track p[0]) {
            <option [value]="p[0]" [selected]="filters().provincia === p[0]">{{ p[1] }}</option>
          }
        </select>
        <select voltNativeSelect aria-label="Precio máximo" (change)="set('max', +$any($event.target).value)">
          <option value="0">Cualquier precio</option>
          @for (v of prices; track v) {
            <option [value]="v" [selected]="filters().max === v">Hasta {{ v.toLocaleString('es-ES') }} €</option>
          }
        </select>
      </div>
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <button voltButton size="sm" [variant]="filters().tipo === '' ? 'solid' : 'outline'" (click)="set('tipo', '')">Todos</button>
        @for (t of tipoOptions; track t[0]) {
          <button voltButton size="sm" [variant]="filters().tipo === t[0] ? 'solid' : 'outline'" (click)="set('tipo', t[0])">{{ t[1] }}</button>
        }
        <span class="ml-auto flex items-center gap-2">
          <span class="text-sm text-muted-foreground" aria-live="polite">
            <strong class="text-foreground">{{ filtered().length.toLocaleString('es-ES') }}</strong>
            {{ filtered().length === 1 ? 'negocio' : 'negocios' }}
          </span>
          <button voltButton size="sm" variant="ghost" (click)="reshuffle()" title="Mostrar en otro orden aleatorio">
            <svg aria-hidden="true" viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M16 3h5v5M4 20 21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/></svg>
            Barajar
          </button>
          @if (active()) {
            <button voltButton size="sm" variant="link" (click)="reset()">Quitar filtros</button>
          }
        </span>
      </div>
    </section>

    @if (visible().length) {
      <ul class="grid list-none gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3">
        @for (r of visible(); track r.s) {
          <li class="animate-[fadeUp_.35s_ease-out_both]"><app-listing-card [row]="r" /></li>
        }
      </ul>
    } @else if (loading()) {
      <ul class="grid list-none gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3">
        @for (i of skeletons; track i) {
          <li class="rounded-xl border border-border p-5">
            <volt-skeleton variant="text" class="mb-3 w-1/3" />
            <volt-skeleton variant="text" class="mb-2 w-full" />
            <volt-skeleton variant="rectangle" class="h-16 w-full" />
          </li>
        }
      </ul>
    } @else {
      <div class="rounded-xl border border-dashed border-border px-6 py-16 text-center">
        <p class="text-lg font-medium">No hay negocios con estos filtros</p>
        <p class="mt-1 text-sm text-muted-foreground">Prueba con otra provincia o sube el precio máximo.</p>
        <button voltButton variant="outline" class="mt-4" (click)="reset()">Quitar filtros</button>
      </div>
    }

    <div #sentinel class="h-px"></div>
    @if (visible().length < filtered().length) {
      <div class="mt-8 flex justify-center">
        <button voltButton variant="outline" (click)="more()">Ver más negocios</button>
      </div>
    }
  `,
})
export class ExplorerComponent {
  /** Anuncios pintados en el build (SEO). */
  readonly initial = input<Row[]>([]);
  /** Filtros fijados por la página (p. ej. /traspasos/hosteleria/). */
  readonly preset = input<Partial<Filters>>({});
  /** [slug, nombre] de provincias con anuncios. */
  readonly provinciaOptions = input<[string, string][]>([]);
  /** Sincroniza los filtros con la URL (?q=&sector=…). */
  readonly syncUrl = input(false);

  protected readonly sectorOptions = Object.entries(SECTORES);
  protected readonly tipoOptions = Object.entries(TIPOS);
  protected readonly prices = PRICES;
  protected readonly skeletons = [1, 2, 3, 4, 5, 6];

  private readonly all = signal<Row[] | null>(null);
  private readonly userFilters = signal<Partial<Filters> | null>(null);
  protected readonly loading = signal(true);
  private readonly limit = signal(PAGE);
  private readonly sentinel = viewChild<ElementRef<HTMLElement>>("sentinel");

  protected readonly filters = computed<Filters>(() => ({ ...EMPTY, ...this.preset(), ...(this.userFilters() ?? {}) }));
  protected readonly provincias = computed(() => this.provinciaOptions());
  protected readonly active = computed(() => {
    const f = this.filters(), p = { ...EMPTY, ...this.preset() };
    return (Object.keys(EMPTY) as (keyof Filters)[]).some((k) => f[k] !== p[k]);
  });
  protected readonly filtered = computed(() => {
    const rows = this.all() ?? this.initial();
    const f = this.filters();
    return rows.filter((r) => matches(r, f));
  });
  protected readonly visible = computed(() => this.filtered().slice(0, this.limit()));

  constructor() {
    const destroyRef = inject(DestroyRef);
    // Solo en el navegador
    afterNextRender(() => {
      if (this.syncUrl()) this.readUrl();
      fetch("/listings-index.json")
        .then((r) => (r.ok ? r.json() : []))
        .then((rows: Row[]) => this.all.set(shuffle(rows)))
        .catch(() => this.all.set(shuffle(this.initial())))
        .finally(() => this.loading.set(false));

      const el = this.sentinel()?.nativeElement;
      if (el && "IntersectionObserver" in window) {
        const io = new IntersectionObserver((e) => e.some((x) => x.isIntersecting) && this.all() && this.more(), {
          rootMargin: "600px",
        });
        io.observe(el);
        destroyRef.onDestroy(() => io.disconnect());
      }
    });
  }

  protected set<K extends keyof Filters>(key: K, value: Filters[K]) {
    this.userFilters.update((f) => ({ ...(f ?? {}), [key]: value }));
    this.limit.set(PAGE);
    this.writeUrl();
  }

  protected reset() {
    this.userFilters.set(null);
    this.limit.set(PAGE);
    this.writeUrl();
  }

  protected reshuffle() {
    this.all.update((rows) => shuffle(rows ?? this.initial()));
    this.limit.set(PAGE);
  }

  protected more() {
    if (this.limit() < this.filtered().length) this.limit.update((n) => n + PAGE);
  }

  private readUrl() {
    const p = new URLSearchParams(location.search);
    const f: Partial<Filters> = {};
    for (const k of ["q", "sector", "provincia", "tipo"] as const) if (p.get(k)) f[k] = p.get(k)!;
    if (p.get("max")) f.max = Number(p.get("max")) || 0;
    if (Object.keys(f).length) this.userFilters.set(f);
  }

  private writeUrl() {
    if (!this.syncUrl() || typeof history === "undefined") return;
    const f = this.filters();
    const qs = new URLSearchParams(
      Object.entries(f).filter(([, v]) => v).map(([k, v]) => [k, String(v)]),
    ).toString();
    history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
  }
}
