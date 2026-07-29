import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ArkItem {
  id?: number;
  name: string;
  category: string;
  description?: string;
  spawn_command?: string;
  crafting_recipe?: Record<string, number>;
  image_url?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl;

  // Testează conexiunea cu baza de date
  getItems(): Observable<ArkItem[]> {
    return this.http.get<ArkItem[]>(`${this.baseUrl}/items`);
  }

  // Testează scraping-ul/wiki API din FastAPI
  testWiki(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/test-wiki`);
  }
}