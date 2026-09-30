import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import {
  VoltCard, VoltTable, VoltTableBody, VoltTableCell, VoltTableHead, VoltTableHeader, VoltTableRow,
} from "@voltui/components";

export interface StatRow { href: string; label: string; count: number; traspasos: number; median: string }

@Component({
  selector: "app-stats-table",
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [VoltCard, VoltTable, VoltTableHeader, VoltTableBody, VoltTableRow, VoltTableHead, VoltTableCell],
  template: `
    <volt-card class="overflow-x-auto p-2">
      <volt-table>
        <volt-table-header>
          <volt-table-row>
            <volt-table-head>{{ label() }}</volt-table-head>
            <volt-table-head class="text-right">Anuncios</volt-table-head>
            <volt-table-head class="text-right">Traspasos</volt-table-head>
            <volt-table-head class="text-right">Precio mediano</volt-table-head>
          </volt-table-row>
        </volt-table-header>
        <volt-table-body>
          @for (r of rows(); track r.href) {
            <volt-table-row>
              <volt-table-cell><a class="font-medium hover:text-primary hover:underline" [href]="r.href">{{ r.label }}</a></volt-table-cell>
              <volt-table-cell class="text-right tabular-nums">{{ r.count }}</volt-table-cell>
              <volt-table-cell class="text-right tabular-nums">{{ r.traspasos }}</volt-table-cell>
              <volt-table-cell class="text-right font-medium tabular-nums">{{ r.median || '—' }}</volt-table-cell>
            </volt-table-row>
          }
        </volt-table-body>
      </volt-table>
    </volt-card>
  `,
})
export class StatsTableComponent {
  readonly label = input("Sector");
  readonly rows = input<StatRow[]>([]);
}
