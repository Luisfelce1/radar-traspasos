import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import {
  VoltAlert, VoltAlertDescription, VoltAlertTitle, VoltBadge, VoltCard, VoltCardContent, VoltCardHeader, VoltCardTitle,
  VoltNativeButton, VoltSeparator, VoltTable, VoltTableBody, VoltTableCell, VoltTableRow,
} from "@voltui/components";

export interface DetailData {
  title: string;
  tipo: string;
  sector: string;
  icon: string;
  price: string;
  priceMuted: boolean;
  summary: string;
  url: string;
  sourceName: string;
  alsoOn: { url: string; name: string }[];
  facts: [string, string][];
  retired: boolean;
  retiredOn?: string;
}

/** Ficha de anuncio: cabecera, resumen, CTA al original y tabla de datos. Render estático. */
@Component({
  selector: "app-listing-detail",
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    VoltCard, VoltCardHeader, VoltCardTitle, VoltCardContent, VoltBadge, VoltNativeButton, VoltSeparator,
    VoltTable, VoltTableBody, VoltTableRow, VoltTableCell, VoltAlert, VoltAlertTitle, VoltAlertDescription,
  ],
  template: `
    @if (d().retired) {
      <volt-alert variant="warning" class="mb-6">
        <volt-alert-title>Anuncio retirado</volt-alert-title>
        <volt-alert-description>Ya no está disponible en el portal de origen (retirado el {{ d().retiredOn }}).</volt-alert-description>
      </volt-alert>
    }

    <header class="mb-8">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <volt-badge [variant]="d().tipo === 'Traspaso' ? 'success' : 'secondary'">{{ d().tipo }}</volt-badge>
        <volt-badge variant="outline">{{ d().icon }} {{ d().sector }}</volt-badge>
      </div>
      <h1 class="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">{{ d().title }}</h1>
      <p class="mt-3 text-3xl font-semibold tracking-tight text-primary" [class.text-muted-foreground]="d().priceMuted">{{ d().price }}</p>
    </header>

    <div class="grid items-start gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
      <volt-card>
        <volt-card-header class="p-6 pb-2"><volt-card-title>Resumen</volt-card-title></volt-card-header>
        <volt-card-content class="p-6 pt-2">
          <p class="leading-relaxed">{{ d().summary }}</p>
          @if (!d().retired) {
            <a voltButton size="lg" class="mt-6 w-full sm:w-auto" [href]="d().url" target="_blank" rel="nofollow noopener">
              Ver anuncio completo en {{ d().sourceName }}
              <svg aria-hidden="true" viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 17 17 7M8 7h9v9"/></svg>
            </a>
          }
          @if (d().alsoOn.length) {
            <p class="mt-4 text-sm text-muted-foreground">
              También publicado en
              @for (a of d().alsoOn; track a.url; let last = $last) {
                <a class="font-medium text-foreground underline underline-offset-4" [href]="a.url" target="_blank" rel="nofollow noopener">{{ a.name }}</a>{{ last ? '.' : ', ' }}
              }
            </p>
          }
          <volt-separator class="my-6" />
          <p class="text-xs text-muted-foreground">
            Resumen propio elaborado a partir de los datos públicos del anuncio. Fotos, descripción completa y
            contacto del anunciante están en el portal de origen.
          </p>
        </volt-card-content>
      </volt-card>

      <volt-card>
        <volt-card-header class="p-6 pb-2"><volt-card-title>Datos del negocio</volt-card-title></volt-card-header>
        <volt-card-content class="p-2 pt-0">
          <volt-table>
            <volt-table-body>
              @for (f of d().facts; track f[0]) {
                <volt-table-row>
                  <volt-table-cell class="w-2/5 text-muted-foreground">{{ f[0] }}</volt-table-cell>
                  <volt-table-cell class="font-medium">{{ f[1] }}</volt-table-cell>
                </volt-table-row>
              }
            </volt-table-body>
          </volt-table>
        </volt-card-content>
      </volt-card>
    </div>
  `,
})
export class ListingDetailComponent {
  readonly d = input<DetailData>({
    title: "", tipo: "", sector: "", icon: "", price: "", priceMuted: true, summary: "", url: "", sourceName: "",
    alsoOn: [], facts: [], retired: false,
  });
}
