import { ChangeDetectionStrategy, Component, computed, input } from "@angular/core";
import {
  VoltBadge, VoltCard, VoltCardContent, VoltCardDescription, VoltCardFooter, VoltCardHeader, VoltCardTitle,
} from "@voltui/components";
import { priceLabel, SECTOR_ICON, SECTORES, TIPOS } from "./model";
import type { Row } from "./model";

const EMPTY_ROW: Row = { s: "", t: "", k: "venta", c: "otros", p: "", u: "", e: 0, m: 0, y: "", o: "", f: "" };

/** Tarjeta de anuncio. Se usa estática (Astro) y dentro del explorador (hidratado). */
@Component({
  selector: "app-listing-card",
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [VoltCard, VoltCardHeader, VoltCardTitle, VoltCardDescription, VoltCardContent, VoltCardFooter, VoltBadge],
  host: { class: "block h-full" },
  template: `
    <a [href]="'/anuncio/' + row().s + '/'" class="group block h-full rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
      <volt-card class="flex h-full flex-col transition duration-200 group-hover:-translate-y-0.5 group-hover:shadow-md group-hover:border-primary/40">
        <volt-card-header class="flex flex-col gap-3 p-5 pb-3">
          <div class="flex items-center justify-between gap-2">
            <span class="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <span aria-hidden="true" class="grid size-7 place-items-center rounded-full bg-muted text-sm">{{ icon() }}</span>
              {{ sector() }}
            </span>
            <volt-badge [variant]="row().k === 'traspaso' ? 'success' : row().k === 'alquiler' ? 'info' : 'secondary'">{{ tipo() }}</volt-badge>
          </div>
          <volt-card-title class="line-clamp-2 text-base leading-snug group-hover:text-primary">{{ row().t }}</volt-card-title>
        </volt-card-header>
        <volt-card-content class="flex-1 px-5 pb-4">
          <p class="text-xl font-semibold tracking-tight" [class.text-muted-foreground]="!row().e">{{ price() }}</p>
          @if (row().y) {
            <volt-card-description class="mt-2 line-clamp-3 text-sm">{{ row().y }}</volt-card-description>
          }
        </volt-card-content>
        <volt-card-footer class="flex items-center justify-between gap-2 border-t border-border px-5 py-3 text-xs text-muted-foreground">
          <span class="inline-flex min-w-0 items-center gap-1">
            <svg aria-hidden="true" viewBox="0 0 24 24" class="size-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>
            <span class="truncate">{{ row().u || 'España' }}</span>
          </span>
          <span class="max-w-[55%] truncate" [title]="row().o">vía {{ row().o }}</span>
        </volt-card-footer>
      </volt-card>
    </a>
  `,
})
export class ListingCardComponent {
  readonly row = input<Row>(EMPTY_ROW);
  protected readonly sector = computed(() => SECTORES[this.row().c] ?? "Negocio");
  protected readonly icon = computed(() => SECTOR_ICON[this.row().c] ?? "📦");
  protected readonly tipo = computed(() => TIPOS[this.row().k] ?? "Venta");
  protected readonly price = computed(() => priceLabel(this.row()));
}
